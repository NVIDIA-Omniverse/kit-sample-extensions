# Calendar widget

To use:

```python
from omni.kit.widget.calendar import Calendar

def build_calendar():
    date_time = datetime.now()
    Calendar(date_time.date())

# you could set the first day of week 0 = Monday...6 = Sunday.
def build_other_calendar():
    date_time = datetime.now()
    Calendar(date_time.date(), first_weekday=0)
```
