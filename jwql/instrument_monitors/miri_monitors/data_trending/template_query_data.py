import sql_interface as sql
from bokeh.plotting import figure, output_file, show
from bokeh.models import BoxAnnotation

import numpy as np

from sklearn.linear_model import LinearRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.utils import check_random_state
from sklearn import metrics

from astropy.time import Time

###############################################

db_file = "miri_database.db"
conn = sql.create_connection(db_file)


query_name = 'IMIR_IC_SCE_DIG_TEMP'

columns = ('start_time, average, deviation')
queried_data = sql.query_data(conn,query_name, columns)

x=[]
y=[]

for item in queried_data:
    x.append(item[0])
    y.append(item[1])
####################################################

X=np.array(x)
Y=np.array(y)

ir = IsotonicRegression()
y_ = ir.fit_transform(X,Y)

lr = LinearRegression()
lr.fit(X[:, np.newaxis], Y) # x needs to be 2d for LinearRegression
y_pred = lr.predict(X[:, np.newaxis])
# output to static HTML file
output_file("lines.html")

# create a new plot with a title and axis labels
p = figure( tools = "pan,box_zoom,reset,save",           \
            title = query_name,                          \
            x_axis_label = 'DOY', y_axis_label='data')

p.background_fill_color = "#efefef"
p.xgrid.grid_line_color = None
#p.add_layout(BoxAnnotation(top=0.23, fill_alpha=0.1, fill_color='red', line_color='red'))
#p.add_layout(BoxAnnotation(bottom=0.24, fill_alpha=0.1, fill_color='red', line_color='red'))


# add a line renderer with legend and line thickness
p.scatter(x, y, color='red', legend = "Data points")
p.line(x, y_, color='green', legend= "Isotonic regression")
#p.line(X, y_pred, color='blue', legend= "Lin. regression")

print('Mean Absolute Error:', metrics.mean_absolute_error(Y, y_pred))
print('Mean Squared Error:', metrics.mean_squared_error(Y, y_pred))
print('Root Mean Squared Error:', np.sqrt(metrics.mean_squared_error(Y, y_pred)))
#p.line(x, y1, legend="deviation", line_color="orange", line_dash="4 4")

p.legend.location = "top_right"
p.legend.click_policy = "hide"

# show the results
show(p)

print('end')
