"""Безопасная логика пакетного переименования. Не изменяет содержимое файлов."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import os
import random
import uuid
from datetime import datetime


@dataclass
class RenameItem:
    source: Path
    target: Path


class RenameError(Exception):
    pass


def build_plan(folder: Path, start: int = 1, step: int = 1,
               prefix: str = "", suffix: str = "_",
               rng=None) -> list[RenameItem]:
    folder = Path(folder)
    if not folder.is_dir():
        raise RenameError("Выбранная папка не существует или недоступна.")
    if step == 0:
        raise RenameError("Шаг нумерации не может быть равен нулю.")
    files = [p for p in folder.iterdir() if p.is_file()]
    (rng or random.SystemRandom()).shuffle(files)
    plan = []
    for i, src in enumerate(files):
        number = start + i * step
        new_name = f"{prefix}{number}{suffix}{src.suffix}"
        if not new_name or new_name in (".", "..") or any(c in new_name for c in '<>:"/\\|?*') or any(ord(c) < 32 for c in new_name):
            raise RenameError(f"Недопустимое имя: {new_name!r}")
        if new_name.endswith(" ") or new_name.endswith("."):
            raise RenameError(f"Имя не может оканчиваться пробелом или точкой: {new_name!r}")
        if len(new_name.encode("utf-16-le")) // 2 > 255:
            raise RenameError(f"Имя слишком длинное для Windows: {new_name!r}")
        device_name = new_name.split(".", 1)[0].upper()
        if device_name in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
            raise RenameError(f"Это зарезервированное имя Windows: {new_name!r}")
        plan.append(RenameItem(src, folder / new_name))
    validate_plan(plan)
    return plan


def validate_plan(plan: list[RenameItem]) -> None:
    sources = {p.source.resolve() for p in plan}
    targets = set()
    for item in plan:
        key = os.path.normcase(str(item.target))
        if key in targets:
            raise RenameError(f"Два файла получат одинаковое имя: {item.target.name}")
        targets.add(key)
        if item.target.exists() and item.target.resolve() not in sources:
            raise RenameError(f"Целевое имя уже занято: {item.target.name}")
        if not os.access(item.source, os.R_OK | os.W_OK):
            raise RenameError(f"Нет прав на чтение или переименование: {item.source.name}")


def execute_plan(plan: list[RenameItem], journal_dir: Path | None = None, write_journal: bool = True) -> Path | None:
    """Двухфазное перемещение: все источники -> уникальные временные имена -> цели."""
    if not plan:
        raise RenameError("В папке нет файлов для переименования.")
    validate_plan(plan)
    token = uuid.uuid4().hex
    staged: list[tuple[Path, Path]] = []
    completed: list[tuple[Path, Path]] = []
    try:
        for item in plan:
            temp = item.source.with_name(f".fsr_tmp_{token}_{len(staged)}")
            if temp.exists():
                raise RenameError(f"Временное имя уже занято: {temp.name}")
            item.source.rename(temp)
            staged.append((temp, item.source))
        for index, (temp, original) in enumerate(staged):
            target = next(x.target for x in plan if x.source == original)
            if target.exists():
                raise RenameError(f"Целевое имя неожиданно занято: {target.name}")
            temp.rename(target)
            completed.append((target, original))
    except Exception as exc:
        # Вернуть уже перемещённые файлы на исходные имена.
        for current, original in reversed(completed):
            try:
                if current.exists() and not original.exists():
                    current.rename(original)
            except OSError:
                pass
        for temp, original in reversed(staged):
            try:
                if temp.exists() and not original.exists():
                    temp.rename(original)
            except OSError:
                pass
        raise RenameError(f"Операция прервана; выполнена попытка восстановления. Причина: {exc}") from exc

    if not write_journal:
        return None
    log_dir = journal_dir or (plan[0].source.parent / ".FileShuffleRenamer")
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"operation_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
    data = [{"old": str(item.source), "new": str(item.target)} for item in plan]
    log_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return log_path


def undo_last(folder: Path) -> str:
    folder = Path(folder)
    log_dir = folder / ".FileShuffleRenamer"
    logs = sorted(log_dir.glob("operation_*.json"), reverse=True) if log_dir.exists() else []
    if not logs:
        raise RenameError("Журнал операций не найден.")
    log = logs[0]
    data = json.loads(log.read_text(encoding="utf-8"))
    reverse = [RenameItem(Path(x["new"]), Path(x["old"])) for x in data]
    # Undo must be safe even if some original names were reused.
    validate_plan(reverse)
    execute_plan(reverse, journal_dir=log_dir, write_journal=False)
    log.unlink(missing_ok=True)
    return f"Восстановлено файлов: {len(reverse)}"
