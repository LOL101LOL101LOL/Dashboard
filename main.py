import subprocess
import sys

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])


install("streamlit")
install("git+https://github.com/im-perativa/streamlit-calendar.git")



import streamlit as st
import pandas as pd
from streamlit_calendar import calendar
from datetime import timedelta
import plotly.express as px


st.set_page_config(page_title="Trading Account Summary", page_icon="📆")


custom_css = """
<style>
/* Adjust the width of the main container */
#root > div:nth-child(1) > div > div > div > div > div:nth-child(2) > div {
    width: 100%;
}

/* Adjust the height of the calendar view */
.fc .fc-view-harness {
    height: 800px;
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)


def load_data(uploaded_file):
    if uploaded_file is not None:
        data = pd.read_csv(uploaded_file)
        data['Open Date'] = pd.to_datetime(data['Open Date'])
        data['Close Date'] = pd.to_datetime(data['Close Date'])
        data['Duration'] = data['Close Date'] - data['Open Date']
        return data
    else:
        return None


uploaded_file = st.file_uploader("Upload your trading CSV file", type=["csv"])
if uploaded_file is not None:
    data = load_data(uploaded_file)


    def prepare_daily_summary(data):
        daily_summary = data.groupby(data['Close Date'].dt.date).agg(
            Net_Profit_Loss=('Profit', 'sum'),
            Max_Drawdown=('Drawdown', 'max'),
            Avg_Trade_Duration=('Duration', 'mean')
        )
        return daily_summary


    def format_duration(td):
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f'{hours:02d}:{minutes:02d}:{seconds:02d}'


    daily_summary = prepare_daily_summary(data)


    def calculate_win_loss_streaks(series):
        series = series.map({'Win': 1, 'Loss': -1, 'Neutral': 0})
        series_diff = series.diff().ne(0)
        series_diff.iloc[0] = True
        streaks = series_diff.cumsum()


        wins = series[series == 1]
        losses = series[series == -1]

        max_win_streak = wins.groupby(streaks).count().max() if not wins.empty else 0
        max_loss_streak = losses.groupby(streaks).count().max() if not losses.empty else 0

        return max_win_streak, max_loss_streak


    daily_profit_loss = data.groupby(['Symbol', 'Close Date'])['Profit'].sum()
    daily_win_loss = daily_profit_loss.apply(lambda x: 'Win' if x > 0 else ('Loss' if x < 0 else 'Neutral'))


    win_loss_streaks = daily_win_loss.groupby(level=0).apply(calculate_win_loss_streaks)
    streaks_df = pd.DataFrame(win_loss_streaks.tolist(), index=win_loss_streaks.index, columns=['Max Win Streak', 'Max Loss Streak'])


    streaks_plot_data = streaks_df.reset_index().melt(id_vars='Symbol', var_name='Streak Type', value_name='Days')


    st.header("Maximum Win and Loss Streaks per Currency Pair")
    fig = px.bar(streaks_plot_data, x='Symbol', y='Days', color='Streak Type', barmode='group', title="Max Win/Loss Streaks per Currency Pair")
    st.plotly_chart(fig)


    events = []
    for date, row in daily_summary.iterrows():
        profit_loss = round(row['Net_Profit_Loss'], 2)
        drawdown = round(row['Max_Drawdown'], 2) if pd.notna(row['Max_Drawdown']) else 'N/A'
        duration = format_duration(row['Avg_Trade_Duration'])


        pl_title = f'P/L: {profit_loss}'
        pl_color = '#FF4B4B' if profit_loss < 0 else '#3DD56D'
        pl_event = {
            "title": pl_title,
            "color": pl_color,
            "start": str(date),
            "end": str(date + timedelta(days=1))
        }
        events.append(pl_event)


        dd_title = f'Max DD: {drawdown}'
        dd_event = {
            "title": dd_title,
            "color": "#808080",
            "start": str(date),
            "end": str(date + timedelta(days=1))
        }
        events.append(dd_event)


        td_title = f'TD: {duration}'
        td_event = {
            "title": td_title,
            "color": "#808080",
            "start": str(date),
            "end": str(date + timedelta(days=1))
        }
        events.append(td_event)


    calendar_options = {
        "navLinks": "true",
    }


    col1, col2, col3 = st.columns([2,2,1])
    with col2:
        if st.button('Reset Calendar View', key='reset_button'):
            calendar_options["initialView"] = "multiMonthYear"

    state = calendar(
        events=events,
        options=calendar_options,
    )

else:
    st.write("Please upload a CSV file to begin.")
