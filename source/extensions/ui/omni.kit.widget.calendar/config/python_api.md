# Public API for module omni.kit.widget.calendar:

## Classes

- class Calendar(AbstractCalendarClass)
  - YEAR_MIN: int
  - YEAR_MAX: int
  - def __init__(self, date: datetime.date, width: Optional[ui.Length] = ui.Pixel(210), height: Optional[ui.Length] = ui.Pixel(200), style: Dict = None, show_combobox: bool = False, day_selected_handler: Callable[[AbstractCalendarClass], None] = None, first_weekday: int = calendar.SUNDAY)
  - [property] def year(self)
  - [property] def month(self)
  - [property] def day(self)
  - def set_date(self, dt: datetime.date)
