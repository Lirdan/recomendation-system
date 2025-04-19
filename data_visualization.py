import sqlite3
import pandas as pd
from bokeh.plotting import figure, output_file, show
from bokeh.transform import cumsum
from bokeh.palettes import Category20, Category10
from math import pi
from bokeh.embed import components
from bokeh.models import ColumnDataSource

def fetch_data(db_path, query):
    """
    Execute a SQL query and return the result as a Pandas DataFrame.

    Parameters:
        db_path (str): Path to the SQLite database.
        query (str): SQL query to execute.

    Returns:
        DataFrame: Query results.
    """
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(query, conn)

def create_strategy_pie_chart(db_path):
    """
    Generate a pie chart showing the distribution of recommendation strategies used.

    Parameters:
        db_path (str): Path to the SQLite database.

    Returns:
        tuple: (script, div) for embedding the Bokeh pie chart.
    """
    # Query for count per recommendation strategy
    query = """
    SELECT recommendation_type, COUNT(*) as count
    FROM event_logs
    GROUP BY recommendation_type
    """
    data = fetch_data(db_path, query)
    # Calculate angles for pie chart
    data['angle'] = data['count']/data['count'].sum() * 2*pi
    # Assign colors based on number of categories
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
        # If there are more than 20 categories, you can repeat the colors or choose a different strategy.
        data['color'] = Category20[20] * (num_categories // 20 + 1)
    # Create Bokeh pie chart
    p = figure(height=455, width=800, title="Розподіл стратегій рекомендацій", toolbar_location=None,
               tools="hover", tooltips="@recommendation_type: @count", x_range=(-0.5, 1.0))
    p.name = 'pie_chart'
    p.wedge(x=0, y=1, radius=0.4,
            start_angle=cumsum('angle', include_zero=True),
            end_angle=cumsum('angle'),
            line_color="white", fill_color='color',
            legend_field='recommendation_type', source=data)
    # Hide axis and grid
    p.axis.axis_label = None
    p.axis.visible = False
    p.grid.grid_line_color = None
    # Return chart components
    script, div = components(p)
    return script, div

def create_conversion_bar_chart(db_path):
    """
    Create a bar chart showing the number of purchases per recommendation strategy.

    Parameters:
        db_path (str): Path to the SQLite database.

    Returns:
        tuple: (script, div) for embedding the Bokeh bar chart.
    """
    query = """
    SELECT recommendation_type, COUNT(*) as count
    FROM event_logs
    WHERE event_type = 'purchase'
    GROUP BY recommendation_type
    """
    # Choose bar colors
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
        colors = Category20[20] * (num_categories // 20 + 1) 
    # Create data source for Bokeh
    source = ColumnDataSource(
        data=dict(recommendation_types=data['recommendation_type'], counts=data['count'], color=colors))
    # Create Bokeh bar chart
    p = figure(x_range=data['recommendation_type'], title="Конверсія за типом рекомендацій",
               toolbar_location=None, tools="",width=800, height=455)
    p.vbar(x='recommendation_types', top='counts', width=0.9, source=source, color='color')
    # Style chart
    p.xgrid.grid_line_color = None
    p.y_range.start = 0
    p.name = 'bar_chart'
    p.y_range.end = max(data['count']) + 10
    p.xaxis.axis_label = "Тип рекомендацій"
    p.yaxis.axis_label = "Кількість конверсій"
    script, div = components(p)
    return script, div

def fetch_ctr_by_recommendation_type(db_path):
    """
    Fetch click-through rate (CTR) statistics by recommendation type.

    CTR = (clicks / views) * 100

    Parameters:
        db_path (str): Path to the SQLite database.

    Returns:
        DataFrame: CTR data with 'recommendation_type', 'clicks', 'views', and 'CTR' columns.
    """
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
    """
    Create a bar chart visualizing CTR (click-through rate) per recommendation type.

    Parameters:
        db_path (str): Path to the SQLite database.

    Returns:
        tuple: (script, div) for embedding the CTR bar chart.
    """
    data = fetch_ctr_by_recommendation_type(db_path)
    source = ColumnDataSource(data)
    # Create CTR bar chart
    p = figure(x_range=data['recommendation_type'], title="CTR за типом рекомендацій",
               toolbar_location=None, height=455, width=800)
    p.vbar(x='recommendation_type', top='CTR', width=0.9, source=source)
    p.name = 'ctr_chart'
    # Style
    p.xgrid.grid_line_color = None
    p.y_range.start = 0
    p.xaxis.axis_label = "Тип рекомендацій"
    p.yaxis.axis_label = "CTR (%)"
    # Optional: add color palette (not currently used in rendering)
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
        data['color'] = Category20[20] * (num_categories // 20 + 1)
    script, div = components(p)
    return script, div
