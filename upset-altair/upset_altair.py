import altair as alt
import pandas as pd

def visualize(
    data=None,
    title="",
    subtitle="",
    sets=None,
    abbre=None,
    sort_by="frequency",
    sort_order="ascending",
    width=1200,
    height=700,
    height_ratio=0.6,
    horizontal_bar_chart_width=300,
    color_range=["#55A8DB", "#3070B5", "#30363F", "#F1AD60", "#DF6234", "#BDC6CA"],
    highlight_color="#EA4667",
    glyph_size=200,
    set_label_bg_size=1000,
    line_connection_size=2,
    horizontal_bar_size=20,
    vertical_bar_label_size=16,
    vertical_bar_padding=20
): 
    """This function generates Altair-based interactive UpSet plots.
    
    Parameters:
        - data (pandas.DataFrame): Tabular data containing the membership of each element (row) in 
            exclusive intersecting sets (column).
        - sets (list): List of set names of interest to show in the UpSet plots. 
            This list reflects the order of sets to be shown in the plots as well.
        - abbre (list): Abbreviated set names.
        - sort_by (str): "frequency" or "degree"
        - sort_order (str): "ascending" or "descending"
        - width (int): Vertical size of the UpSet plot.
        - height (int): Horizontal size of the UpSet plot.
        - height_ratio (float): Ratio of height between upper and under views, ranges from 0 to 1.
        - horizontal_bar_chart_width (int): Width of horizontal bar chart on the bottom-right.
        - color_range (list): Color to encode sets.
        - highlight_color (str): Color to encode intersecting sets upon mouse hover.
        - glyph_size (int): Size of UpSet glyph (⬤).
        - set_label_bg_size (int): Size of label background in the horizontal bar chart.
        - line_connection_size (int): width of lines in matrix view.
        - horizontal_bar_size (int): Height of bars in the horizontal bar chart.
        - vertical_bar_label_size (int): Font size of texts in the vertical bar chart on the top.
        - vertical_bar_padding (int): Gap between a pair of bars in the vertical bar charts.
    
    Return:
        Altair `Chart` object.
    """

    if (data is None) or (sets is None):
        print("No data and/or a list of sets are provided")
        return
    if (height_ratio < 0) or (1 < height_ratio):
        print("height_ratio set to 0.5")
        height_ratio = 0.5
    if len(sets) != len(abbre):
        abbre = None
        print("Dropping the `abbre` list because the lengths of `sets` and `abbre` are not identical.")

    """
    Data Preprocessing
    """
    data["count"] = 0
    data = data[sets + ["count"]]
    data = data.groupby(sets).count().reset_index()
    
    data["intersection_id"] = data.index
    data["degree"] = data[sets].sum(axis=1)
    data = data.sort_values(by=["count"], ascending=True if sort_order == "ascending" else False)
    
    data = pd.melt(data, id_vars=[
        "intersection_id", "count", "degree"
    ])
    data = data.rename(columns={"variable": "set", "value": "is_intersect"})
    
    if abbre == None:
        abbre = sets

    set_to_abbre = pd.DataFrame([ [sets[i], abbre[i]] for i in range(len(sets)) ], columns=["set", "set_abbre"])
    set_to_order = pd.DataFrame([ [sets[i], 1 + sets.index(sets[i])] for i in range(len(sets)) ], columns=["set", "set_order"])

    degree_calculation = ""
    for s in sets:
        degree_calculation += f"(isDefined(datum['{s}']) ? datum['{s}'] : 0)"
        if sets[-1] != s:
            degree_calculation += "+"
    
    """
    Selections
    """
    legend_selection = alt.selection_multi(fields=["set"], bind="legend")
    color_selection = alt.selection_single(fields=["intersection_id"], on="mouseover")
    opacity_selection = alt.selection_single(fields=["intersection_id"])
    
    """
    Styles
    """
    vertical_bar_chart_height = height * height_ratio
    matrix_height = height - vertical_bar_chart_height
    matrix_width = width - horizontal_bar_chart_width
    
    vertical_bar_size = min(30, width / len(data["intersection_id"].unique().tolist()) - vertical_bar_padding)
    
    main_color = "#3A3A3A"
    brush_opacity = alt.condition(~opacity_selection, alt.value(1), alt.value(0.6))
    brush_color = alt.condition(~color_selection, alt.value(main_color), alt.value(highlight_color))
    
    is_show_horizontal_bar_label_bg = len(abbre[0]) <= 2
    horizontal_bar_label_bg_color = "white" if is_show_horizontal_bar_label_bg else "black"

    x_sort = alt.Sort(
        field="count" if sort_by == "frequency" else "degree",
        order=sort_order
    )
    tooltip = [
        alt.Tooltip("max(count):Q", title="Cardinality"),
        alt.Tooltip("degree:Q", title="Degree")
    ]
    
    """
    Plots
    """
    # To use native interactivity in Altair, we are using the data transformation functions
    # supported in Altair.
    base = alt.Chart(data).transform_filter(
        legend_selection
    ).transform_pivot(
        # Right before this operation, columns should be:
        # `count`, `set`, `is_intersect`, (`intersection_id`, `degree`, `set_order`, `set_abbre`)
        # where (fields with brackets) should be dropped and recalculated later.
        "set",
        op="max",
        groupby=["intersection_id", "count"],
        value="is_intersect"
    ).transform_aggregate(
        # count, set1, set2, ...
        count="sum(count)",
        groupby=sets
    ).transform_calculate(
        # count, set1, set2, ...
        degree=degree_calculation
    ).transform_filter(
        # count, set1, set2, ..., degree
        alt.datum["degree"] != 0
    ).transform_window(
        # count, set1, set2, ..., degree
        intersection_id="row_number()",
        frame=[None, None]
    ).transform_fold(
        # count, set1, set2, ..., degree, intersection_id
        sets, as_=["set", "is_intersect"]
    ).transform_lookup(
        # count, set, is_intersect, degree, intersection_id
        lookup="set",
        from_=alt.LookupData(set_to_abbre, "set", ["set_abbre"])
    ).transform_lookup(
        # count, set, is_intersect, degree, intersection_id, set_abbre
        lookup="set",
        from_=alt.LookupData(set_to_order, "set", ["set_order"])
    ).transform_filter(
        # Make sure to remove the filtered sets.
        legend_selection
    ).transform_window(
        # count, set, is_intersect, degree, intersection_id, set_abbre
        set_order="distinct(set)",
        frame=[None, 0],
        sort=[{"field": "set_order"}]
    )
    # Now, we have data in the following format:
    # count, set, is_intersect, degree, intersection_id, set_abbre

    # Cardinality by intersecting sets (vertical bar chart)
    vertical_bar = base.mark_bar(color=main_color, size=vertical_bar_size).encode(
        x=alt.X(
            "intersection_id:N", 
            axis=alt.Axis(grid=False, labels=False, ticks=False, domain=True), 
            sort=x_sort,
            title=None
        ),
        y=alt.Y(
            "max(count):Q",
            axis=alt.Axis(grid=False, tickCount=3, orient='right'),
            title="Intersection Size"
        ),
        color=brush_color,
        tooltip=tooltip
    ).properties(
        width=matrix_width,
        height=vertical_bar_chart_height
    )

    vertical_bar_text = vertical_bar.mark_text(
        color=main_color, 
        dy=-10,
        size=vertical_bar_label_size
    ).encode(
        text=alt.Text("count:Q", format=".0f")
    )

    vertical_bar_chart = (vertical_bar + vertical_bar_text).add_selection(
        color_selection
    )
    
    # UpSet glyph view (matrix view)
    circle_bg = vertical_bar.mark_circle(size=glyph_size, opacity=1).encode(
        x=alt.X(
            "intersection_id:N", 
            axis=alt.Axis(grid=False, labels=False, ticks=False, domain=False), 
            sort=x_sort,
            title=None
        ),
        y=alt.Y(
            "set_order:N",
            axis=alt.Axis(grid=False, labels=False, ticks=False, domain=False),
            title=None
        ),
        color=alt.value("#E6E6E6")
    ).properties(
        height=matrix_height
    )

    rect_bg = circle_bg.mark_rect().transform_filter(
        alt.datum["set_order"] % 2 == 1
    ).encode(
        color=alt.value("#F7F7F7")
    )

    circle = circle_bg.transform_filter(
        alt.datum["is_intersect"] == 1
    ).encode(
        color=brush_color
    )

    line_connection = vertical_bar.mark_bar(size=line_connection_size, color=main_color).transform_filter(
        alt.datum["is_intersect"] == 1
    ).encode(
        y=alt.Y("min(set_order):N"),
        y2=alt.Y2("max(set_order):N")
    )
    
    matrix_view = (circle + rect_bg + circle_bg + line_connection + circle).add_selection(
        # Duplicate `circle` is to properly show tooltips.
        color_selection
    )

    # Cardinality by sets (horizontal bar chart)
    horizontal_bar_label_bg = base.mark_circle(size=set_label_bg_size).encode(
        y=alt.Y(
            "set_order:N",
            axis=alt.Axis(grid=False, labels=False, ticks=False, domain=False),
            title=None,
        ),
        color=alt.Color(
            "set:N",
            scale=alt.Scale(domain=sets, range=color_range),
            title=None
        ),
        opacity=alt.value(1)
    )
    horizontal_bar_label = horizontal_bar_label_bg.mark_text(
            align=("center" if is_show_horizontal_bar_label_bg else "center")
        ).encode(
        text=alt.Text("set_abbre:N"),
        color=alt.value(horizontal_bar_label_bg_color)
    )
    horizontal_bar_axis = (horizontal_bar_label_bg + horizontal_bar_label) if is_show_horizontal_bar_label_bg else horizontal_bar_label
    
    horizontal_bar = horizontal_bar_label_bg.mark_bar(
        size=horizontal_bar_size
    ).transform_filter(
        alt.datum["is_intersect"] == 1
    ).encode(
        x=alt.X(
            "sum(count):Q",
            axis=alt.Axis(grid=False, tickCount=3),
            title="Set Size"
        )
    ).properties(
        width=horizontal_bar_chart_width
    )
    
    # Concat Plots
    upsetaltair = alt.vconcat(
        vertical_bar_chart,
        alt.hconcat(
            matrix_view, 
            horizontal_bar_axis, horizontal_bar, # horizontal bar chart
            spacing=5
        ).resolve_scale(
            y="shared"
        ),
        spacing=20
    ).add_selection(
        legend_selection
    )
    
    # Apply top-level configuration
    upsetaltair = upsetaltair_top_level_configuration(
        upsetaltair, 
        legend_orient="top",
        legend_symbol_size=set_label_bg_size / 2.0
    ).properties(
        title={
            "text": title,
            "subtitle": subtitle,
            "fontSize": 20,
            "fontWeight": 500,
            "subtitleColor": main_color,
            "subtitleFontSize": 14
        }
    )
    
    return upsetaltair

# Top-level altair configuration
def upsetaltair_top_level_configuration(
    base,
    legend_orient="top-left",
    legend_symbol_size=30
):
    return base.configure_view(
        stroke=None
    ).configure_title(
        fontSize=18,
        fontWeight=400,
        anchor="start",
        subtitlePadding=10
    ).configure_axis(
        labelFontSize=14,
        labelFontWeight=300,
        titleFontSize=16,
        titleFontWeight=400,
        titlePadding=10
    ).configure_legend(
        titleFontSize=16,
        titleFontWeight=400,
        labelFontSize=14,
        labelFontWeight=300,
        padding=20,
        orient=legend_orient,
        symbolType="circle",
        symbolSize=legend_symbol_size,
    ).configure_concat(
        spacing=0
    )

if __name__ == '__main__':
    
    # Use the latest data from https://figshare.com/articles/covid_symptoms_table_csv/12148893
    df = pd.read_csv("https://ndownloader.figshare.com/files/22339791")

    upset_altair = visualize(
        data=df.copy(),
        title="Symptoms Reported by Users of the COVID Symptom Tracker App",
        subtitle=[
            "Story & Data: https://www.nature.com/articles/d41586-020-00154-w",
            "Altair-based UpSet Plot: https://github.com/hms-dbmi/upset-altair-notebook"
        ],
        sets=["Shortness of Breath", "Diarrhea", "Fever", "Cough", "Anosmia", "Fatigue"],
        abbre=["B", "D", "Fe", "C", "A", "Fa"],
        sort_by="frequency",
        sort_order="ascending",
    )
    
    upset_altair.display()

