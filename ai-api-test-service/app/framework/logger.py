from pathlib import Path


def get_logger(run_id, log_dir):
    folder = Path(log_dir)
    folder.mkdir(parents=True, exist_ok=True)
    log_path = folder / f'{run_id}.log'
    lines = []

    def log(message):
        text = str(message)
        lines.append(text)
        with log_path.open('a', encoding='utf-8') as handle:
            handle.write(text + '\n')

    return log, str(log_path), lines
