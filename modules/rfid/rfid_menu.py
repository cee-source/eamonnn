from core.menu import MenuEntry
from core.config_manager import ConfigManager


def build_rfid_menu(config: ConfigManager, display=None) -> list[MenuEntry]:
    from modules.rfid.rfid_reader import RFIDReader
    reader = RFIDReader(config, display)

    return [
        MenuEntry(label='Read Card',        action=reader.scan_and_display),
        MenuEntry(label='Write Text',       action=lambda: _write_prompt(reader, display)),
        MenuEntry(label='Full Dump',        action=lambda: _dump_card(reader, config, display)),
        MenuEntry(label='Saved Cards',      action=reader.list_saved),
    ]


def _write_prompt(reader, display) -> None:
    text = input('Enter text to write: ')
    ok = reader.write_text(text)
    msg = ['Write OK!' if ok else 'Write FAILED']
    if display:
        import time
        display.draw_message(msg)
        time.sleep(2)
    else:
        print(msg[0])


def _dump_card(reader, config, display) -> None:
    import time
    if display:
        display.draw_message(['Dump Card', 'Hold card near reader...', 'Scanning all sectors...'])
    dump = reader.dump_card()
    if dump:
        saved = config.save_capture('rfid', dump, prefix=f'dump_{dump["uid_hex"]}')
        lines = ['Dump Complete!', f'UID: {dump["uid_hex"]}',
                 f'Sectors: {len(dump["sectors"])}', f'Saved: {saved.split("/")[-1]}']
    else:
        lines = ['Dump Failed', 'No card detected']
    if display:
        display.draw_message(lines)
        time.sleep(3)
    else:
        print('\n'.join(lines))
