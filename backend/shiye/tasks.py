import re
from datetime import date, datetime, timedelta, timezone

from .exports import block_text
from .models import TaskItem


def extract_tasks(doc, reference: date):
    tasks = []
    for page in doc.pages:
        for block in page.blocks:
            text = block_text(block).strip()
            if not re.search(r"提交|截止|作业|会议|上课|报名|集合|答辩|考试|活动|参加|开会|讲座|面试|提醒", text):
                continue
            for line in text.splitlines():
                if not line.strip():
                    continue
                found_date = ""
                explicit = re.search(r"(?:(20\d{2})[年/.-])?(\d{1,2})[月/.-](\d{1,2})日?", line)
                try:
                    if explicit:
                        found_date = date(int(explicit[1] or reference.year), int(explicit[2]), int(explicit[3])).isoformat()
                    elif "后天" in line:
                        found_date = (reference+timedelta(days=2)).isoformat()
                    elif "明天" in line:
                        found_date = (reference+timedelta(days=1)).isoformat()
                    elif "今天" in line:
                        found_date = reference.isoformat()
                    else:
                        week = re.search(r"(下|本|这)?周([一二三四五六日天])", line)
                        if week:
                            weekday = "一二三四五六日".index("日" if week[2] == "天" else week[2])
                            monday = reference - timedelta(days=reference.weekday())
                            found_date = (monday+timedelta(days=weekday+(7 if week[1] == "下" else 0))).isoformat()
                except ValueError:
                    pass
                match = re.search(r"(?:(上午|下午|晚上|中午))?\s*(\d{1,2})(?:[:：](\d{2})|点(半|\d{1,2}分?)?)", line)
                found_time = ""
                if match:
                    hour = int(match[2])
                    minute = int(match[3] or ("30" if match[4] == "半" else (match[4] or "0").replace("分", "")))
                    if match[1] in {"下午", "晚上", "中午"} and hour < 12:
                        hour += 12
                    if hour < 24 and minute < 60:
                        found_time = f"{hour:02}:{minute:02}"
                kind = "deadline" if re.search(r"截止|提交|交作业|报名", line) else "event"
                tasks.append(TaskItem(title=line[:120], source_text=line[:5000], page_id=page.id, date=found_date, time=found_time, kind=kind, note=f"规则提取，参考日 {reference.isoformat()}；未给时间时不会补 23:59。请人工确认。"))
    return tasks[:100]


def ical_escape(value):
    return value.replace("\\", "\\\\").replace("\r", "").replace("\n", "\\n").replace(";", "\\;").replace(",", "\\,")


def fold_line(line):
    parts, current = [], ""
    for char in line:
        if len((current+char).encode("utf-8")) > 73:
            parts.append(current)
            current = " "
        current += char
    parts.append(current)
    return "\r\n".join(parts)


def export_ics(items: list[TaskItem]):
    selected = [t for t in items if t.confirmed]
    if not selected:
        raise ValueError("请至少确认一条有日期的事项")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Shiye//CN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for task in selected:
        if not task.title.strip():
            raise ValueError("请为已确认事项填写标题")
        try:
            day = date.fromisoformat(task.date)
        except ValueError as exc:
            raise ValueError(f"事项‘{task.title[:20]}’缺少有效日期") from exc
        component = "VTODO" if task.kind == "deadline" else "VEVENT"
        lines.extend([f"BEGIN:{component}", f"UID:{task.id}@shiye.local", f"DTSTAMP:{stamp}", "SUMMARY:"+ical_escape(task.title), "DESCRIPTION:"+ical_escape(task.source_text)])
        field = "DUE" if task.kind == "deadline" else "DTSTART"
        if task.time:
            try:
                local = datetime.fromisoformat(f"{task.date}T{task.time}")
                if local.tzinfo is not None:
                    raise ValueError("只接受本地时分")
                utc = local.replace(tzinfo=timezone(timedelta(hours=8))).astimezone(timezone.utc)
            except ValueError as exc:
                raise ValueError("时间格式应为 HH:MM") from exc
            lines.append(f"{field}:{utc.strftime('%Y%m%dT%H%M%SZ')}")
        else:
            lines.append(f"{field};VALUE=DATE:{day.strftime('%Y%m%d')}")
            if component == "VEVENT":
                lines.append(f"DTEND;VALUE=DATE:{(day+timedelta(days=1)).strftime('%Y%m%d')}")
        if task.location:
            lines.append("LOCATION:"+ical_escape(task.location))
        lines.append(f"END:{component}")
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold_line(line) for line in lines)+"\r\n"
