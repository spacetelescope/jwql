from bokeh.models import DatetimeTickFormatter

plot_x_axis_format = DatetimeTickFormatter(
        hours=  ["%Y-%m-%d ,%H:%M:%S.%f"],
        days=   ["%Y-%m-%d, %H:%M"],
        months= ["%Y-%m-%d, %H:%M"],
        years=  ["%Y-%m-%d"],
    )
