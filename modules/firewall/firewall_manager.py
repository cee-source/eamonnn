"""
Firewall manager using iptables.
Supports viewing rules, adding/removing rules, preset profiles,
and saving/loading rule sets.
Requires root (sudo) to modify rules.
"""
from __future__ import annotations

import logging
import subprocess
from typing import Optional

log = logging.getLogger(__name__)


def _run(cmd: list[str], check: bool = True) -> tuple[int, str, str]:
    """Run a shell command, return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, '', 'Command timed out'
    except FileNotFoundError:
        return 1, '', f'Command not found: {cmd[0]}'


def _iptables(*args) -> tuple[bool, str]:
    code, out, err = _run(['sudo', 'iptables'] + list(args))
    return code == 0, out or err


class FirewallManager:
    def __init__(self, config=None) -> None:
        self._config = config

    # -----------------------------------------------------------------------
    # Status
    # -----------------------------------------------------------------------

    def is_available(self) -> bool:
        code, _, _ = _run(['which', 'iptables'])
        return code == 0

    def get_status(self) -> dict:
        """Return current rule counts per chain."""
        ok, out = _iptables('-L', '-n', '--line-numbers', '-v')
        return {'available': ok, 'rules': out}

    def list_rules(self, table: str = 'filter') -> list[str]:
        ok, out = _iptables('-t', table, '-L', '-n', '--line-numbers', '-v')
        if not ok:
            return [f'Error: {out}']
        return out.splitlines()

    def list_rules_numeric(self) -> list[str]:
        """Returns simplified list: chain, target, proto, source, dest."""
        ok, out = _iptables('-L', '-n', '--line-numbers')
        if not ok:
            return [f'Error: {out}']
        lines = []
        for line in out.splitlines():
            line = line.strip()
            if line:
                lines.append(line)
        return lines

    # -----------------------------------------------------------------------
    # Basic rule management
    # -----------------------------------------------------------------------

    def block_ip(self, ip: str, direction: str = 'both') -> tuple[bool, str]:
        """Block an IP address. direction: 'in', 'out', or 'both'."""
        results = []
        if direction in ('in', 'both'):
            ok, msg = _iptables('-A', 'INPUT', '-s', ip, '-j', 'DROP')
            results.append(('INPUT', ok, msg))
        if direction in ('out', 'both'):
            ok, msg = _iptables('-A', 'OUTPUT', '-d', ip, '-j', 'DROP')
            results.append(('OUTPUT', ok, msg))

        success = all(ok for _, ok, _ in results)
        summary = ', '.join(f'{chain}: {"OK" if ok else msg}' for chain, ok, msg in results)
        if success:
            log.info('Blocked IP %s (%s)', ip, direction)
        else:
            log.error('Failed to block IP %s: %s', ip, summary)
        return success, summary

    def unblock_ip(self, ip: str, direction: str = 'both') -> tuple[bool, str]:
        """Remove block on an IP address."""
        results = []
        if direction in ('in', 'both'):
            ok, msg = _iptables('-D', 'INPUT', '-s', ip, '-j', 'DROP')
            results.append(('INPUT', ok, msg))
        if direction in ('out', 'both'):
            ok, msg = _iptables('-D', 'OUTPUT', '-d', ip, '-j', 'DROP')
            results.append(('OUTPUT', ok, msg))

        success = all(ok for _, ok, _ in results)
        if success:
            log.info('Unblocked IP %s (%s)', ip, direction)
        return success, ', '.join(f'{c}: {"OK" if ok else m}' for c, ok, m in results)

    def block_port(self, port: int, protocol: str = 'tcp',
                   direction: str = 'in') -> tuple[bool, str]:
        """Block incoming or outgoing traffic on a port."""
        chain = 'INPUT' if direction == 'in' else 'OUTPUT'
        flag = '--dport' if direction == 'in' else '--dport'
        ok, msg = _iptables('-A', chain, '-p', protocol,
                            flag, str(port), '-j', 'DROP')
        if ok:
            log.info('Blocked port %d/%s (%s)', port, protocol, direction)
        return ok, msg

    def unblock_port(self, port: int, protocol: str = 'tcp',
                     direction: str = 'in') -> tuple[bool, str]:
        chain = 'INPUT' if direction == 'in' else 'OUTPUT'
        ok, msg = _iptables('-D', chain, '-p', protocol,
                            '--dport', str(port), '-j', 'DROP')
        if ok:
            log.info('Unblocked port %d/%s (%s)', port, protocol, direction)
        return ok, msg

    def allow_port(self, port: int, protocol: str = 'tcp',
                   direction: str = 'in') -> tuple[bool, str]:
        """Explicitly allow traffic on a port."""
        chain = 'INPUT' if direction == 'in' else 'OUTPUT'
        ok, msg = _iptables('-I', chain, '1', '-p', protocol,
                            '--dport', str(port), '-j', 'ACCEPT')
        if ok:
            log.info('Allowed port %d/%s (%s)', port, protocol, direction)
        return ok, msg

    def delete_rule_by_number(self, chain: str, number: int) -> tuple[bool, str]:
        """Delete a rule by its line number (from list_rules_numeric)."""
        ok, msg = _iptables('-D', chain.upper(), str(number))
        if ok:
            log.info('Deleted rule #%d from %s', number, chain)
        return ok, msg

    def flush_chain(self, chain: str = 'INPUT') -> tuple[bool, str]:
        """Remove all rules from a chain."""
        ok, msg = _iptables('-F', chain.upper())
        if ok:
            log.info('Flushed chain %s', chain)
        return ok, msg

    def flush_all(self) -> tuple[bool, str]:
        """Flush ALL chains — effectively disables the firewall."""
        ok1, _ = _iptables('-F')
        ok2, _ = _iptables('-X')  # delete user chains
        ok3, _ = _iptables('-t', 'nat', '-F')
        ok = ok1 and ok2 and ok3
        if ok:
            log.warning('All firewall rules flushed!')
        return ok, 'All rules cleared' if ok else 'Some flush commands failed'

    # -----------------------------------------------------------------------
    # Default policies
    # -----------------------------------------------------------------------

    def set_policy(self, chain: str, policy: str) -> tuple[bool, str]:
        """Set default policy for a chain: ACCEPT or DROP."""
        ok, msg = _iptables('-P', chain.upper(), policy.upper())
        if ok:
            log.info('Set %s policy to %s', chain, policy)
        return ok, msg

    def lockdown(self) -> tuple[bool, str]:
        """Block all incoming connections except established ones."""
        cmds = [
            ['-P', 'INPUT', 'DROP'],
            ['-P', 'FORWARD', 'DROP'],
            ['-P', 'OUTPUT', 'ACCEPT'],
            ['-A', 'INPUT', '-m', 'state', '--state', 'ESTABLISHED,RELATED', '-j', 'ACCEPT'],
            ['-A', 'INPUT', '-i', 'lo', '-j', 'ACCEPT'],   # allow loopback
        ]
        for args in cmds:
            ok, msg = _iptables(*args)
            if not ok:
                log.error('Lockdown step failed: %s -> %s', args, msg)
                return False, f'Failed at: {" ".join(args)}: {msg}'
        log.warning('Firewall LOCKDOWN activated')
        return True, 'Lockdown active: all inbound blocked except established'

    def allow_ssh(self) -> tuple[bool, str]:
        """Allow SSH (port 22) — run this before lockdown to avoid locking yourself out."""
        ok, msg = _iptables('-I', 'INPUT', '1', '-p', 'tcp', '--dport', '22', '-j', 'ACCEPT')
        if ok:
            log.info('SSH (port 22) allowed')
        return ok, msg

    # -----------------------------------------------------------------------
    # Preset profiles
    # -----------------------------------------------------------------------

    PROFILES = {
        'open':     'Allow all traffic (flush rules)',
        'ssh_only': 'Allow SSH only, drop all other inbound',
        'web':      'Allow HTTP(80) + HTTPS(443) + SSH(22)',
        'lockdown': 'Drop ALL inbound (keep established)',
    }

    def apply_profile(self, profile: str) -> tuple[bool, str]:
        profile = profile.lower()
        if profile == 'open':
            ok, msg = self.flush_all()
            self.set_policy('INPUT', 'ACCEPT')
            self.set_policy('OUTPUT', 'ACCEPT')
            return ok, 'Open: all traffic allowed'

        elif profile == 'ssh_only':
            self.flush_all()
            self.set_policy('INPUT', 'DROP')
            self.set_policy('OUTPUT', 'ACCEPT')
            _iptables('-A', 'INPUT', '-m', 'state', '--state', 'ESTABLISHED,RELATED', '-j', 'ACCEPT')
            _iptables('-A', 'INPUT', '-i', 'lo', '-j', 'ACCEPT')
            ok, msg = self.allow_ssh()
            return ok, 'SSH-only: port 22 open, all else dropped'

        elif profile == 'web':
            self.flush_all()
            self.set_policy('INPUT', 'DROP')
            self.set_policy('OUTPUT', 'ACCEPT')
            _iptables('-A', 'INPUT', '-m', 'state', '--state', 'ESTABLISHED,RELATED', '-j', 'ACCEPT')
            _iptables('-A', 'INPUT', '-i', 'lo', '-j', 'ACCEPT')
            self.allow_ssh()
            self.allow_port(80, 'tcp')
            self.allow_port(443, 'tcp')
            return True, 'Web profile: SSH + HTTP + HTTPS open'

        elif profile == 'lockdown':
            return self.lockdown()

        return False, f'Unknown profile: {profile}'

    # -----------------------------------------------------------------------
    # Save / restore rules
    # -----------------------------------------------------------------------

    def save_rules(self, path: str) -> tuple[bool, str]:
        """Save current rules to a file using iptables-save."""
        code, out, err = _run(['sudo', 'iptables-save'])
        if code != 0:
            return False, err
        try:
            with open(path, 'w') as f:
                f.write(out)
            log.info('Firewall rules saved to %s', path)
            return True, f'Saved to {path}'
        except OSError as e:
            return False, str(e)

    def restore_rules(self, path: str) -> tuple[bool, str]:
        """Restore rules from a file using iptables-restore."""
        code, out, err = _run(['sudo', 'iptables-restore', path])
        if code == 0:
            log.info('Firewall rules restored from %s', path)
            return True, f'Restored from {path}'
        return False, err
