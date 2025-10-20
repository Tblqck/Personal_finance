# advanced_time_frame_pipeline_v2.py
import re
import calendar
from datetime import datetime, timedelta, time as dtime

# timezone (std lib)
try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Africa/Lagos")
except Exception:
    TZ = None

# ---------- CONFIG ----------
WORDS_NUM = {
    "zero":0,"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,"ten":10,
    "eleven":11,"twelve":12,"thirteen":13,"fourteen":14,"fifteen":15,"sixteen":16,"seventeen":17,"eighteen":18,
    "nineteen":19,"twenty":20,"thirty":30,"forty":40
}

COMMON_FIXES = {
    "moring":"morning","tommorrow":"tomorrow","tommorow":"tomorrow","wednessday":"wednesday",
    "wednsday":"wednesday","thuersday":"thursday","wednesay":"wednesday","thrusday":"thursday",
    "firday":"friday","beech":"beach","mnth":"month","mnths":"months"
}

TIME_WORDS = {
    "noon": (12,0), "midday": (12,0), "midnight": (0,0),
    "morning": (9,0), "afternoon": (13,0), "evening": (18,0), "night": (20,0)
}

MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
for i,m in enumerate(calendar.month_abbr):
    if m:
        MONTHS[m.lower()] = i

WEEKDAYS = {d:i for i,d in enumerate(["monday","tuesday","wednesday","thursday","friday","saturday","sunday"])}

# ---------- HELPERS ----------
def now_local():
    if TZ:
        return datetime.now(TZ)
    return datetime.utcnow()

def words_to_digits(text: str) -> str:
    if not WORDS_NUM:
        return text
    def repl(m):
        return str(WORDS_NUM.get(m.group(0), m.group(0)))
    return re.sub(r'\b(' + '|'.join(map(re.escape, WORDS_NUM.keys())) + r')\b', repl, text)

def clamp_day(year:int, month:int, day:int) -> int:
    _, mdays = calendar.monthrange(year, month)
    return max(1, min(day, mdays))

def add_months(dt: datetime, months: int) -> datetime:
    tzinfo = dt.tzinfo
    m = dt.month - 1 + months
    y = dt.year + m // 12
    mm = m % 12 + 1
    day = clamp_day(y, mm, dt.day)
    return datetime(y, mm, day, dt.hour, dt.minute, dt.second, tzinfo=tzinfo)

def parse_time_token(tok: str):
    """Return dict or None: {hour, minute, explicit_ampm(bool), hint(str or None)}"""
    if not tok:
        return None
    s = tok.strip().lower()
    # map words
    if s in TIME_WORDS:
        h,m = TIME_WORDS[s]; return {"hour":h,"minute":m,"explicit":True,"hint":s}
    # 24h hh:mm
    m = re.match(r'^(\d{1,2}):(\d{2})$', s)
    if m:
        hh = int(m.group(1)); mm = int(m.group(2))
        return {"hour":hh,"minute":mm,"explicit":True,"hint":None}
    # hh:mm am/pm
    m = re.match(r'^(\d{1,2}):(\d{2})\s*(am|pm)$', s)
    if m:
        hh = int(m.group(1)); mm = int(m.group(2)); ap = m.group(3)
        if ap == "pm" and hh != 12: hh += 12
        if ap == "am" and hh == 12: hh = 0
        return {"hour":hh,"minute":mm,"explicit":True,"hint":ap}
    # hh am/pm
    m = re.match(r'^(\d{1,2})\s*(am|pm)$', s)
    if m:
        hh = int(m.group(1)); ap = m.group(2)
        if ap == "pm" and hh != 12: hh += 12
        if ap == "am" and hh == 12: hh = 0
        return {"hour":hh,"minute":0,"explicit":True,"hint":ap}
    # bare number (ambiguous)
    m = re.match(r'^(\d{1,2})$', s)
    if m:
        hh = int(m.group(1)); return {"hour":hh,"minute":0,"explicit":False,"hint":None}
    return None

def fmt_time_12(dt: datetime):
    return dt.strftime("%I:%M%p").lstrip("0").lower()

# ---------- CORE PIPELINE ----------
def extract_time_frame_full(message: str):
    text_raw = (message or "").strip()
    text = text_raw.lower()
    # normalize common typos, convert words to digits
    for bad,good in COMMON_FIXES.items():
        text = re.sub(r'\b' + re.escape(bad) + r'\b', good, text)
    text = words_to_digits(text)
    text = re.sub(r"\btomm?orr?ow'?s?\b", "tomorrow", text)  # fix for tomorrows / tomorrow's


    now = now_local()
    assumptions = {
        "year_assumed": False,
        "month_assumed": False,
        "week_assumed": False,
        "day_assumed": False,
        "time_assumed": False,
        "time_ambiguous": False
    }
    ambiguous_options = []
    clarification = None

    # 1) YEAR resolver
    explicit_year = None
    m = re.search(r'\b(20\d{2})\b', text)
    if m:
        explicit_year = int(m.group(1))
        assumptions["year_assumed"] = False
    else:
        assumptions["year_assumed"] = True
        explicit_year = now.year

    # 2) MONTH resolver
    month_specified = None
    month_offset = 0
    # explicit month name
    for name in MONTHS:
        if re.search(r'\b' + re.escape(name) + r'\b', text):
            month_specified = MONTHS[name]; break
    # next/in N months
    m = re.search(r'\bnext\s+(\d+)\s+months?\b', text) or re.search(r'\bin\s+(\d+)\s+months?\b', text)
    if m:
        month_offset = int(m.group(1))
    elif re.search(r'\bnext\s+month\b', text):
        month_offset = 1
    elif re.search(r'\bthis\s+month\b', text):
        month_offset = 0

    if month_specified is None and month_offset == 0:
        # default to current month
        month_specified = now.month
        assumptions["month_assumed"] = True
    else:
        assumptions["month_assumed"] = False

    # 3) WEEK resolver
    week_offset = 0
    m = re.search(r'\bnext\s+(\d+)\s+weeks?\b', text) or re.search(r'\bin\s+(\d+)\s+weeks?\b', text)
    if m:
        week_offset = int(m.group(1))
    elif re.search(r'\bnext\s+week\b', text):
        week_offset = 1
    elif re.search(r'\bthis\s+week\b', text):
        week_offset = 0
    if week_offset != 0:
        assumptions["week_assumed"] = False
    else:
        assumptions["week_assumed"] = True

    # also support "in N days" or "after N days"
    rel_days = None
    m = re.search(r'\bin\s+(\d+)\s+days?\b', text) or re.search(r'\bafter\s+(\d+)\s+days?\b', text)
    if m:
        rel_days = int(m.group(1))

    # 4) DAY resolver (weekday or day-of-month)
    day_of_month = None
    weekday = None
    # day-of-month like "15th of november" or "15 of november" or "on the 15"
    m = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+of\s+([a-z]+)\b', text)
    if m:
        day_of_month = int(m.group(1))
        mon_word = m.group(2)
        if mon_word in MONTHS:
            month_specified = MONTHS[mon_word]
            assumptions["month_assumed"] = False
    if day_of_month is None:
        m = re.search(r'\bon\s+the\s+(\d{1,2})(?:st|nd|rd|th)?\b', text)
        if m:
            day_of_month = int(m.group(1))
    # weekday
    for wname, idx in WEEKDAYS.items():
        if re.search(r'\b' + re.escape(wname) + r'\b', text):
            weekday = wname
            break
    # "day after tomorrow"
    if re.search(r'\bday after tomorrow\b', text):
        rel_days = 2

    if day_of_month is None and weekday is None and rel_days is None:
        assumptions["day_assumed"] = True
    else:
        assumptions["day_assumed"] = False

    # 5) TIME resolver
    # find tokens: hh:mm am/pm, hh am/pm, hh:mm (24h), by/at hh, textual times
    time_token = None
    m = re.search(r'\b(\d{1,2}:\d{2}\s*(?:am|pm)?)\b', text)
    if not m:
        m = re.search(r'\b(\d{1,2}\s*(?:am|pm))\b', text)
    if not m:
        m = re.search(r'\b(\d{1,2}:\d{2})\b', text)
    if not m:
        m = re.search(r'\b(?:by|at)\s+(\d{1,2})\b', text)
    if m:
        time_token = m.group(1)
    if not time_token:
        # textual like "in the afternoon", "noon", "evening"
        m = re.search(r'\b(in the\s+)?(morning|afternoon|evening|night|noon|midday|midnight)\b', text)
        if m:
            time_token = m.group(2)

    parsed_time = parse_time_token(time_token) if time_token else None

    # Start building the base date following your order:
    # year -> month -> week -> day -> time
    base = now.replace(hour=0, minute=0, second=0, microsecond=0)
    # YEAR
    base = base.replace(year=explicit_year)
    # MONTH
    if month_specified is not None and month_offset == 0:
        # if month specified and < current month and year assumed, probably next year
        tgt_month = month_specified
        y = base.year
        if tgt_month < now.month and assumptions["year_assumed"]:
            y += 1
        try:
            base = base.replace(year=y, month=tgt_month, day=1)
        except Exception:
            base = add_months(base, 1)
    elif month_offset:
        base = add_months(base, month_offset)
    # WEEK
    if week_offset:
        base = base + timedelta(weeks=week_offset)
    # relative days override week/month if present
    if rel_days is not None:
        base = base + timedelta(days=rel_days)

    # DAY: prefer explicit day_of_month else weekday else keep base day
    final_date = None
    if day_of_month is not None:
        y, mo = base.year, base.month
        d = clamp_day(y, mo, day_of_month)
        final_date = base.replace(year=y, month=mo, day=d)
        # if in past, advance by one month if month not explicit
        if final_date <= now and (month_specified is None and month_offset == 0 and rel_days is None):
            final_date = add_months(final_date, 1)
    elif weekday:
        # compute the target weekday within the *week of base*
        # week start = Monday
        base_monday = base - timedelta(days=base.weekday())
        target_idx = WEEKDAYS[weekday]
        candidate_day = base_monday + timedelta(days=target_idx)
        # if candidate_day <= now, push forward a week (user expects future)
        if candidate_day <= now:
            candidate_day += timedelta(weeks=1)
        final_date = candidate_day
    else:
        final_date = base

    # TIME: apply parsed_time or defaults
    time_assumed = False
    time_ambiguous = False
    ambiguous_options = []
    chosen_dt = None

    if parsed_time:
        if parsed_time["explicit"]:
            # explicit absolute hour (24h or converted)
            hh = parsed_time["hour"]; mm = parsed_time["minute"]
            chosen_dt = final_date.replace(hour=hh, minute=mm, second=0, microsecond=0)
        else:
            # ambiguous hour (no am/pm). Use context hints
            hh = parsed_time["hour"] % 12
            mm = parsed_time["minute"]
            # check context hints
            pm_hint = bool(re.search(r'\b(afternoon|pm|evening|night|noon|midday)\b', text))
            am_hint = bool(re.search(r'\b(morning|am)\b', text))
            # special: if hour==12, prefer pm (noon) when ambiguous
            if hh == 12 or parsed_time["hour"] == 12:
                prefer_pm = True
            else:
                prefer_pm = False

            cand_am = final_date.replace(hour=hh if hh != 12 else 0, minute=mm, second=0, microsecond=0)
            cand_pm = final_date.replace(hour=(hh if hh != 12 else 0)+12, minute=mm, second=0, microsecond=0)

            # choose using hints
            if am_hint and not pm_hint:
                chosen_dt = cand_am
            elif pm_hint and not am_hint:
                chosen_dt = cand_pm
            elif prefer_pm:
                chosen_dt = cand_pm
                time_ambiguous = True
            else:
                # pick nearest future occurrence (either today or next day)
                diff_am = (cand_am - now).total_seconds()
                diff_pm = (cand_pm - now).total_seconds()
                if diff_am <= 0:
                    diff_am += 24*3600
                if diff_pm <= 0:
                    diff_pm += 24*3600
                if diff_am <= diff_pm:
                    chosen_dt = cand_am
                else:
                    chosen_dt = cand_pm
                # if similar distances, mark ambiguous
                if abs(diff_am - diff_pm) < 3600:  # within 1 hour
                    time_ambiguous = True
                if time_ambiguous:
                    ambiguous_options = [cand_am, cand_pm]
                    assumptions["time_ambiguous"] = True
                    assumptions["time_assumed"] = True
        # ensure chosen_dt in future; if <= now advance intelligently
        if chosen_dt <= now:
            # if weekday specified, move by weeks until in future
            if weekday:
                while chosen_dt <= now:
                    chosen_dt += timedelta(weeks=1)
            elif day_of_month:
                while chosen_dt <= now:
                    chosen_dt = add_months(chosen_dt, 1)
            else:
                while chosen_dt <= now:
                    chosen_dt += timedelta(days=1)
    else:
        # no time token -> default to 09:00am
        chosen_dt = final_date.replace(hour=9, minute=0, second=0, microsecond=0)
        time_assumed = True
        assumptions["time_assumed"] = True
        clarification = "No time specified; defaulted to 09:00am."

    # ensure tz-aware
    if TZ and chosen_dt.tzinfo is None:
        chosen_dt = chosen_dt.replace(tzinfo=TZ)

    # final safety: if still in the past, push forward (one cycle)
    if chosen_dt <= now:
        if weekday:
            while chosen_dt <= now:
                chosen_dt += timedelta(weeks=1)
        elif day_of_month:
            while chosen_dt <= now:
                chosen_dt = add_months(chosen_dt, 1)
        else:
            while chosen_dt <= now:
                chosen_dt += timedelta(days=1)

    timestamp = int(chosen_dt.timestamp())
    diff = chosen_dt - now
    days = diff.days
    hours = int(diff.total_seconds() // 3600) % 24
    if days >= 1:
        human_rel = f"in {days} day{'s' if days != 1 else ''}"
    elif hours >= 1:
        human_rel = f"in {hours} hour{'s' if hours != 1 else ''}"
    else:
        mins = int(diff.total_seconds() // 60)
        human_rel = f"in {mins} minute{'s' if mins != 1 else ''}"

    # prepare ambiguous option strings
    ambiguous_options_str = [fmt_time_12(c) for c in ambiguous_options]

    result = {
        "date": chosen_dt.strftime("%Y-%m-%d"),
        "time": fmt_time_12(chosen_dt),
        "timestamp": timestamp,
        "summary": f"{chosen_dt.strftime('%a, %b %d %Y %I:%M%p')} ({human_rel})",
        "normalized": text,
        "assumptions": assumptions,
        "ambiguous_options": ambiguous_options_str,
        "clarification": clarification,
        "original_message": text_raw
    }
    return result