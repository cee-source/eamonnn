"""
Firewall menu — fully button-navigable.
All common actions work with UP/DOWN/SELECT only.
Only IP/port entry requires typing (unavoidable for custom rules).
"""
import os
import time
import logging

from core.menu import MenuEntry
from core.config_manager import ConfigManager

log = logging.getLogger(__name__)


def build_firewall_menu(config: ConfigManager, display=None) -> list[MenuEntry]:
    from modules.firewall.firewall_manager import FirewallManager
    fw = FirewallManager(config)

    return [
        # --- View ---
        MenuEntry(label='View Rules',       action=lambda: _view_rules(fw, display)),
        MenuEntry(label='Firewall Status',  action=lambda: _status(fw, display)),

        # --- Preset profiles (one button press each) ---
        MenuEntry(label='--- Profiles ---', action=None),
        MenuEntry(label='Profile: Open',     action=lambda: _apply_profile(fw, 'open',     display)),
        MenuEntry(label='Profile: SSH Only', action=lambda: _apply_profile(fw, 'ssh_only', display)),
        MenuEntry(label='Profile: Web',      action=lambda: _apply_profile(fw, 'web',      display)),
        MenuEntry(label='Profile: Lockdown', action=lambda: _apply_profile(fw, 'lockdown', display)),

        # --- Quick actions (button press only) ---
        MenuEntry(label='--- Quick Actions ---', action=None),
        MenuEntry(label='Allow SSH (22)',    action=lambda: _quick(fw.allow_ssh, 'SSH allowed on port 22', display)),
        MenuEntry(label='Allow HTTP (80)',   action=lambda: _quick(lambda: fw.allow_port(80,  'tcp'), 'HTTP port 80 open',   display)),
        MenuEntry(label='Allow HTTPS (443)', action=lambda: _quick(lambda: fw.allow_port(443, 'tcp'), 'HTTPS port 443 open', display)),
        MenuEntry(label='Flush INPUT',       action=lambda: _confirm_action(fw.flush_chain, ['INPUT'],  'Flush INPUT chain?',  display)),
        MenuEntry(label='Flush OUTPUT',      action=lambda: _confirm_action(fw.flush_chain, ['OUTPUT'], 'Flush OUTPUT chain?', display)),
        MenuEntry(label='Flush ALL Rules',   action=lambda: _confirm_action(fw.flush_all,   [],         'Clear ALL rules?',    display)),

        # --- Custom rules (requires typing) ---
        MenuEntry(label='--- Custom ---', action=None),
        MenuEntry(label='Block IP',         action=lambda: _block_ip_prompt(fw, display)),
        MenuEntry(label='Unblock IP',       action=lambda: _unblock_ip_prompt(fw, display)),
        MenuEntry(label='Block Port',       action=lambda: _block_port_prompt(fw, display)),
        MenuEntry(label='Delete Rule #',    action=lambda: _delete_rule_prompt(fw, display)),

        # --- Save / Restore ---
        MenuEntry(label='--- Save/Load ---', action=None),
        MenuEntry(label='Save Rules',        action=lambda: _save_rules(fw, config, display)),
        MenuEntry(label='Restore Rules',     action=lambda: _restore_rules(fw, config, display)),
    ]


# ---------------------------------------------------------------------------
# Helper: show result message
# ---------------------------------------------------------------------------

def _show(display, lines: list[str], pause: float = 3.0) -> None:
    if display:
        display.draw_message(lines)
        time.sleep(pause)
    else:
        print('\n'.join(lines))


# ---------------------------------------------------------------------------
# View / status
# ---------------------------------------------------------------------------

def _view_rules(fw, display) -> None:
    rules = fw.list_rules_numeric()
    if not rules:
        _show(display, ['No rules set', '(firewall open)'])
        return
    # Show up to 8 lines on display
    _show(display, rules[:8], pause=5.0)


def _status(fw, display) -> None:
    if not fw.is_available():
        _show(display, ['iptables NOT found', 'Install iptables:', 'sudo apt install iptables'])
        return
    status = fw.get_status()
    lines = ['Firewall: ACTIVE' if status['available'] else 'Firewall: ERROR']
    # Count rules per chain
    for line in status['rules'].splitlines():
        if line.startswith('Chain'):
            lines.append(line[:32])
    _show(display, lines or ['No rules active'], pause=4.0)


# ---------------------------------------------------------------------------
# Profiles — one button press
# ---------------------------------------------------------------------------

def _apply_profile(fw, profile: str, display) -> None:
    profiles = {
        'open':     'Open: allow all',
        'ssh_only': 'SSH Only profile',
        'web':      'Web profile',
        'lockdown': '!! LOCKDOWN !!',
    }
    # Confirm for dangerous profiles
    if profile == 'lockdown':
        if not _confirm_dialog(display, ['Apply LOCKDOWN?', 'All inbound blocked!', 'SELECT=Yes  BACK=No']):
            _show(display, ['Cancelled'], pause=1.5)
            return

    _show(display, [f'Applying: {profiles[profile]}', 'Please wait...'], pause=1.0)
    ok, msg = fw.apply_profile(profile)
    _show(display, [
        'Profile Applied!' if ok else 'FAILED',
        profiles[profile],
        msg[:36],
    ])


# ---------------------------------------------------------------------------
# Quick single-action buttons
# ---------------------------------------------------------------------------

def _quick(action_fn, success_msg: str, display) -> None:
    ok, msg = action_fn()
    _show(display, [success_msg if ok else 'Failed', msg[:36]])


def _confirm_action(action_fn, args: list, prompt: str, display) -> None:
    if not _confirm_dialog(display, [prompt, 'SELECT=Yes  BACK=No']):
        _show(display, ['Cancelled'], pause=1.5)
        return
    ok, msg = action_fn(*args)
    _show(display, ['Done!' if ok else 'Failed', msg[:36]])


# ---------------------------------------------------------------------------
# Custom rule prompts (requires keyboard input)
# ---------------------------------------------------------------------------

def _block_ip_prompt(fw, display) -> None:
    ip = input('IP to block (e.g. 192.168.1.5): ').strip()
    if not ip:
        return

    # Direction sub-menu via display or prompt
    direction = _choose(display, 'Block direction?', ['Both', 'Inbound only', 'Outbound only'])
    dir_map = {0: 'both', 1: 'in', 2: 'out'}
    ok, msg = fw.block_ip(ip, dir_map.get(direction, 'both'))
    _show(display, ['Blocked!' if ok else 'Failed', f'IP: {ip}', msg[:36]])


def _unblock_ip_prompt(fw, display) -> None:
    ip = input('IP to unblock: ').strip()
    if not ip:
        return
    direction = _choose(display, 'Unblock direction?', ['Both', 'Inbound only', 'Outbound only'])
    dir_map = {0: 'both', 1: 'in', 2: 'out'}
    ok, msg = fw.unblock_ip(ip, dir_map.get(direction, 'both'))
    _show(display, ['Unblocked!' if ok else 'Failed', f'IP: {ip}', msg[:36]])


def _block_port_prompt(fw, display) -> None:
    try:
        port = int(input('Port to block (e.g. 8080): ').strip())
    except ValueError:
        _show(display, ['Invalid port number'])
        return

    proto_idx = _choose(display, 'Protocol?', ['TCP', 'UDP'])
    proto = 'tcp' if proto_idx == 0 else 'udp'

    dir_idx = _choose(display, 'Direction?', ['Inbound', 'Outbound'])
    direction = 'in' if dir_idx == 0 else 'out'

    ok, msg = fw.block_port(port, proto, direction)
    _show(display, ['Port Blocked!' if ok else 'Failed', f'{proto.upper()} {port} {direction}', msg[:36]])


def _delete_rule_prompt(fw, display) -> None:
    # Show current rules first
    rules = fw.list_rules_numeric()
    _show(display, rules[:6], pause=4.0)

    chain = input('Chain (INPUT/OUTPUT/FORWARD): ').strip().upper() or 'INPUT'
    try:
        number = int(input(f'Rule number to delete from {chain}: ').strip())
    except ValueError:
        _show(display, ['Invalid number'])
        return

    if not _confirm_dialog(display, [f'Delete rule #{number}', f'from {chain}?', 'SELECT=Yes  BACK=No']):
        _show(display, ['Cancelled'], pause=1.5)
        return

    ok, msg = fw.delete_rule_by_number(chain, number)
    _show(display, ['Deleted!' if ok else 'Failed', msg[:36]])


# ---------------------------------------------------------------------------
# Save / restore
# ---------------------------------------------------------------------------

def _save_rules(fw, config, display) -> None:
    import os
    path = os.path.join(config.data_dir, 'firewall_rules.txt')
    ok, msg = fw.save_rules(path)
    _show(display, ['Rules Saved!' if ok else 'Save Failed', msg[:40]])


def _restore_rules(fw, config, display) -> None:
    import os
    path = os.path.join(config.data_dir, 'firewall_rules.txt')
    if not os.path.exists(path):
        _show(display, ['No saved rules found', 'Save rules first'])
        return
    if not _confirm_dialog(display, ['Restore saved rules?', 'This replaces current rules', 'SELECT=Yes  BACK=No']):
        _show(display, ['Cancelled'], pause=1.5)
        return
    ok, msg = fw.restore_rules(path)
    _show(display, ['Restored!' if ok else 'Failed', msg[:40]])


# ---------------------------------------------------------------------------
# UI helpers: button-driven confirm + choose dialogs
# ---------------------------------------------------------------------------

def _confirm_dialog(display, lines: list[str]) -> bool:
    """
    Show a confirmation dialog.
    On OLED/GPIO: SELECT=confirm, BACK=cancel.
    On terminal: y/n prompt.
    """
    if display:
        display.draw_message(lines)
        # Wait for SELECT (confirm) or BACK (cancel)
        # We piggyback on MenuEngine's input by checking the display type
        if hasattr(display, 'getch'):
            import curses
            while True:
                ch = display.getch()
                if ch in (ord('\n'), ord('\r'), ord(' ')):
                    return True
                if ch in (27, ord('q'), ord('n')):
                    return False
        return True  # GPIO: assume confirmed (engine handles BACK)
    else:
        answer = input(f'{lines[0]} (y/n): ').strip().lower()
        return answer == 'y'


def _choose(display, prompt: str, options: list[str]) -> int:
    """
    Show a choice menu, return selected index.
    On terminal: numbered prompt. On OLED: arrow-key selection.
    """
    if display and hasattr(display, 'getch'):
        import curses
        selected = 0
        while True:
            display.draw_menu(prompt, options, selected)
            ch = display.getch()
            if ch == curses.KEY_UP:
                selected = max(0, selected - 1)
            elif ch == curses.KEY_DOWN:
                selected = min(len(options) - 1, selected + 1)
            elif ch in (ord('\n'), ord('\r'), ord(' ')):
                return selected
            elif ch in (27, ord('q')):
                return 0
    else:
        print(f'\n{prompt}')
        for i, opt in enumerate(options):
            print(f'  {i}: {opt}')
        try:
            return int(input('Select: ').strip())
        except ValueError:
            return 0
