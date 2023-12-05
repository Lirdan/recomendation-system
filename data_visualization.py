import sqlite3
import pandas as pd
from bokeh.plotting import figure, output_file, show
from bokeh.transform import cumsum
from bokeh.palettes import Category20, Category10
from math import pi
from bokeh.embed import components
from bokeh.models import ColumnDataSource

def fetch_data(db_path, query):
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(query, conn)

def create_strategy_pie_chart(db_path):
    query = """
    SELECT recommendation_type, COUNT(*) as count
    FROM event_logs
    GROUP BY recommendation_type
    """
    data = fetch_data(db_path, query)

    data['angle'] = data['count']/data['count'].sum() * 2*pi
    num_categories = len(data)
    if num_categories == 1:
        data['color'] = ["#404040"]
    elif num_categories == 2:
        data['color'] = ["#404040", "#CC0000"]
    elif num_categories <= 10:
        data['color'] = Category10[num_categories]
    elif num_categories <= 20:
        data['color'] = Category20[num_categories]
    else:
        # Если категорий больше 20, можно повторять цвета или выбрать другую стратегию
        data['color'] = Category20[20] * (num_categories // 20 + 1)

    p = figure(height=455, width=800, title="Розподіл стратегій рекомендацій", toolbar_location=None,
               tools="hover", tooltips="@recommendation_type: @count", x_range=(-0.5, 1.0))
    p.name = 'pie_chart'
    p.wedge(x=0, y=1, radius=0.4,
            start_angle=cumsum('angle', include_zero=True),
            end_angle=cumsum('angle'),
            line_color="white", fill_color='color',
            legend_field='recommendation_type', source=data)

    p.axis.axis_label = None
    p.axis.visible = False
    p.grid.grid_line_color = None

    script, div = components(p)
    return script, div

def create_conversion_bar_chart(db_path):
    query = """
    SELECT recommendation_type, COUNT(*) as count
    FROM event_logs
    WHERE event_type = 'purchase'
    GROUP BY recommendation_type
    """
    data = fetch_data(db_path, query)

    num_categories = len(data)
    if num_categories == 1:
        colors = ["#404040"]
    elif num_categories == 2:
        colors = ["#404040", "#CC0000"]
    elif num_categories <= 10:
        colors = Category10[num_categories]
    elif num_categories <= 20:
        colors = Category20[num_categories]
    else:
        colors = Category20[20] * (num_categories // 20 + 1)  # Повторение цветов для более 20 категорий

    source = ColumnDataSource(
        data=dict(recommendation_types=data['recommendation_type'], counts=data['count'], color=colors))

    p = figure(x_range=data['recommendation_type'], title="Конверсія за типом рекомендацій",
               toolbar_location=None, tools="",width=800, height=455)
    p.vbar(x='recommendation_types', top='counts', width=0.9, source=source, color='color')

    p.xgrid.grid_line_color = None
    p.y_range.start = 0
    p.name = 'bar_chart'
    p.y_range.end = max(data['count']) + 10
    p.xaxis.axis_label = "Тип рекомендацій"
    p.yaxis.axis_label = "Кількість конверсій"
    script, div = components(p)
    return script, div

def fetch_ctr_by_recommendation_type(db_path):
    query = """
    SELECT 
        recommendation_type,
        SUM(case when event_type = 'click' then 1 else 0 end) as clicks,
        SUM(case when event_type = 'view' then 1 else 0 end) as views
    FROM 
        event_logs
    GROUP BY 
        recommendation_type;
    """
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(query, conn)
    df['CTR'] = (df['clicks'] / df['views']) * 100
    return df
def plot_ctr_by_recommendation_type(db_path):
    data = fetch_ctr_by_recommendation_type(db_path)
    source = ColumnDataSource(data)

    p = figure(x_range=data['recommendation_type'], title="CTR за типом рекомендацій",
               toolbar_location=None, height=455, width=800)
    p.vbar(x='recommendation_type', top='CTR', width=0.9, source=source)
    p.name = 'ctr_chart'
    p.xgrid.grid_line_color = None
    p.y_range.start = 0
    p.xaxis.axis_label = "Тип рекомендацій"
    p.yaxis.axis_label = "CTR (%)"
    num_categories = len(data)
    if num_categories == 1:
        data['color'] = ["#404040"]
    elif num_categories == 2:
        data['color'] = ["#404040", "#CC0000"]
    elif num_categories <= 10:
        data['color'] = Category10[num_categories]
    elif num_categories <= 20:
        data['color'] = Category20[num_categories]
    else:
        # Если категорий больше 20, можно повторять цвета или выбрать другую стратегию
        data['color'] = Category20[20] * (num_categories // 20 + 1)
    script, div = components(p)
    return script, div