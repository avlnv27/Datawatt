import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import timedelta, datetime  
import src.textual.text as txt 
from src.textual.tools import *
from src.indicators.interactive_plot import display_date_range

### FONCTION A RETRAVAILLER ET NON MISE A JOUR

def display_solar_interactive_plot(test2):
    """
    Display interactive plot for solar production and consumption data.
    Shows excedent and autoconsumption data if available.
    
    Args:
        test2: DataFrame containing consumption data and possibly solar data
    """
    # Check if solar data columns exist
    has_excedent = 'Excedent' in test2.columns
    has_autoconsumption = 'Autoconsumption' in test2.columns
    
    if not (has_excedent or has_autoconsumption):
        st.warning("Aucune donnée solaire détectée dans votre fichier.")
        return
    
    # Get consumption column name
    consumption_col = 'Total Consumption (kWh)' if 'Total Consumption (kWh)' in test2.columns else 'Consumption (kWh)'
    
    # Calculate total production if both excedent and autoconsumption exist
    if has_excedent and has_autoconsumption:
        if "Total Production" not in test2.columns:
            test2["Total Production"] = test2["Excedent"] + test2["Autoconsumption"]
    
    # Add new section for solar ratio indicators
    st.markdown("## Indicateurs de performance solaire")
    
    # Calculate and display Global Autoconsumption Ratio
    if has_autoconsumption and has_excedent:
        # Calculate annual values
        annual_data = test2.resample('Y').sum(numeric_only=True)
        
        # Prepare metrics for each year
        for year_idx, year_data in annual_data.iterrows():
            year = year_idx.year
            
            # Calculate global autoconsumption ratio
            total_autoconsumption = year_data["Autoconsumption"]
            total_production = year_data["Total Production"]
            
            if total_production > 0:
                total_consumption = year_data[consumption_col]
                global_ratio = (total_autoconsumption / total_consumption) * 100
                
                # Calculate consumption from solar percentage

                solar_contribution = (total_production / total_consumption) * 100 if total_consumption > 0 else 0
                
                # Display metrics in cards
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"""
                    <div style="border-radius: 10px; border: 2px solid #FF9800; padding: 15px; text-align: center; margin-bottom: 20px;">
                        <h3 style="margin-top: 0;">Taux d'autoconsommation {year}</h3>
                        <p style="font-size: 2.2em; font-weight: bold; color: #FF9800; margin: 10px 0;">{global_ratio:.1f}%</p>
                        <p style="font-size: 0.9em; color: #666;">Pourcentage de votre production solaire<br>que vous consommez directement</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div style="border-radius: 10px; border: 2px solid #7C4DFF; padding: 15px; text-align: center; margin-bottom: 20px;">
                        <h3 style="margin-top: 0;">Production solaire {year}</h3>
                        <p style="font-size: 2.2em; font-weight: bold; color: #7C4DFF; margin: 10px 0;">{solar_contribution:.1f}%</p>
                        <p style="font-size: 0.9em; color: #666;">Pourcentage de votre consommation<br>couverte par votre production solaire</p>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Calculate and display Hourly Relative Consumption Ratio
        st.markdown("### Taux d'autoconsommation")
        
        # User can select which year to analyze
        selected_year_hourly = st.selectbox(
            "Sélectionnez une année pour l'analyse",
            options=test2['Year'].unique(),
            index=0,
            key="hourly_ratio_year"
        )
        
        # Filter data for selected year
        year_data = test2[test2['Year'] == selected_year_hourly]
        
        if not year_data.empty:
            # Group by hour and calculate average ratios
            hourly_stats = []
            
            # For each hour of the day
            for hour in range(24):
                # Filter data for this hour
                hour_data = year_data[year_data.index.hour == hour]
                
                if not hour_data.empty:
                    # Calculate sum for the hour
                    hour_autoconsumption = hour_data["Autoconsumption"].sum()
                    hour_consumption = hour_data['Consumption (kWh)'].sum()
                    hour_total = hour_consumption + hour_autoconsumption  # This might double count, adjust if needed
                    
                    # Calculate ratio with safety check
                    if hour_total > 0:
                        ratio = min((hour_autoconsumption / hour_total) * 100, 100)  # Cap at 100%
                    else:
                        ratio = 0
                    
                    # Store hour and ratio
                    hourly_stats.append({
                        "hour": hour,
                        "ratio": ratio,
                        "autoconsumption": hour_autoconsumption,
                        "consumption": hour_consumption
                    })
            
            # Create dataframe from hourly stats
            hourly_df = pd.DataFrame(hourly_stats)
            
            # Create figure for hourly ratios
            fig_hourly = go.Figure()
            
            # Add trace for ratio
            fig_hourly.add_trace(go.Scatter(
                x=hourly_df["hour"],
                y=hourly_df["ratio"],
                mode='lines+markers',
                name='Taux d\'autoconsommation',
                line=dict(color='#FF9800', width=3),
                marker=dict(size=8),
                hovertemplate="Heure: %{x}:00<br>Taux d'autoconsommation: %{y:.1f}%<extra></extra>"
            ))
            
            # Update layout
            fig_hourly.update_layout(
                title=f'Taux d\'autoconsommation pour {selected_year_hourly}',
                xaxis_title='Heure de la journée',
                yaxis_title='Taux d\'autoconsommation (%)',
                xaxis=dict(
                    tickmode='array',
                    tickvals=list(range(0, 24)),
                    ticktext=[f"{h:02d}:00" for h in range(0, 24)]
                ),
                yaxis=dict(
                    range=[0, 100]
                ),
                margin=dict(l=50, r=50, t=60, b=50),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                hovermode='closest'
            )
            
            # Add reference lines for different levels
            fig_hourly.add_shape(
                type="line",
                x0=0, y0=25, x1=23, y1=25,
                line=dict(color="rgba(255, 152, 0, 0.3)", width=1, dash="dash"),
            )
            
            fig_hourly.add_shape(
                type="line",
                x0=0, y0=50, x1=23, y1=50,
                line=dict(color="rgba(255, 152, 0, 0.5)", width=1, dash="dash"),
            )
            
            fig_hourly.add_shape(
                type="line",
                x0=0, y0=75, x1=23, y1=75,
                line=dict(color="rgba(255, 152, 0, 0.7)", width=1, dash="dash"),
            )
            
            # Display the chart
            st.plotly_chart(fig_hourly, use_container_width=True)
            
            # Add explanation
            st.info("""
            **Taux d'autoconsommation**: Ce graphique montre, pour chaque heure de la journée, le pourcentage de votre 
            consommation électrique qui est couvert par votre propre production solaire. Un taux élevé pendant les heures 
            ensoleillées indique une bonne synchronisation entre votre production et votre consommation.
            """)
    else:
        st.warning("""
        Les indicateurs de performance solaire nécessitent des données d'autoconsommation et de réinjection.
        Ces colonnes ne sont pas disponibles dans vos données.
        """)
    
    # Add this at the end of the function after the time_range visualizations
    st.markdown("---")
    with st.expander("Comment interpréter les indicateurs solaires", expanded=False):
        st.markdown("""
        ### Les indicateurs clés d'autoconsommation
        
        **Taux d'autoconsommation**: Représente le pourcentage de votre production solaire que vous consommez 
        directement, sans la réinjecter dans le réseau. Un taux élevé (>70%) est généralement considéré comme optimal
        et indique que vous utilisez efficacement votre production.
        
        **Taux d'autoconsommation horaire**: Vous permet d'identifier à quelles heures de la journée vous 
        consommez le plus votre propre production solaire. Idéalement, vous voudriez synchroniser vos usages 
        énergétiques avec les périodes de forte production solaire.
        
        ### Comment améliorer ces indicateurs
        
        1. **Déplacer les consommations**: Programmez vos appareils énergivores (lave-linge, lave-vaisselle, pompe 
           de piscine, etc.) pendant les heures de fort ensoleillement, généralement entre 10h et 16h.
        
        2. **Stockage énergétique**: Envisagez l'installation de batteries domestiques pour stocker l'excédent 
           de production et l'utiliser en soirée.
        
        3. **Automatisation**: Des systèmes domotiques peuvent activer automatiquement certains appareils 
           lorsque votre production solaire est élevée.
                    
        ## Autres indicateurs
                    
        **Production solaire**: Indique quelle proportion de votre consommation totale d'électricité est couverte 
        par votre propre production solaire. Une valeur élevée représente une bonne production énergétique et 
        montre un potentiel pour augmenter votre autoconsommation avec une batterie.
        
        """)
    
    # Check if autoconsumption data exists but is mostly zeros (keep this part from the original code)
    if has_autoconsumption and test2["Autoconsumption"].sum() < 0.1 * test2['Consumption (kWh)'].sum():
        st.warning("""
        **Note importante** : Les valeurs d'autoconsommation semblent très faibles par rapport à votre consommation totale. 
        Si vous possédez des panneaux solaires, vérifiez que vos données d'autoconsommation sont correctement mesurées.
        """)

    # Display date range information
    # display_date_range(test2)  # Retiré car maintenant affiché dans la sidebar
    
    # Get consumption column name
    consumption_col = 'Total Consumption (kWh)' if 'Total Consumption (kWh)' in test2.columns else 'Consumption (kWh)'

    # Display the start date and end date
    start_date = test2.index.min().strftime('%Y-%m-%d')
    end_date = test2.index.max().strftime('%Y-%m-%d')

    # Create figure
    fig = go.Figure()
    
    # Define colors for different data types
    color_map = {
        'Consumption': '#1E88E5',  # Blue
        'Excedent': '#26A69A',     # Turquoise
        'Autoconsumption': '#FF9800',  # Orange
        'Total Production': '#7C4DFF'  # Purple
    }

    # Main page for user input
    time_range = st.radio("Choisissez une période :", 
                         ("Année", "Saison", "Semaine", "Jour"), 
                         index=0, 
                         key="time_range_solar", 
                         horizontal=True)

    # User can select which data to display
    data_to_show = []
    
    st.markdown("#### Données à afficher")
    col1, col2 = st.columns(2)
    
    with col1:
        show_consumption = st.checkbox("Consommation", value=True, key="show_consumption_solar")
        if show_consumption:
            data_to_show.append(consumption_col)
        
        if has_excedent:
            show_excedent = st.checkbox("Excédent (réinjecté)", value=True, key="show_excedent_solar")
            if show_excedent:
                data_to_show.append("Excedent")
    
    with col2:
        if has_autoconsumption:
            show_autoconsumption = st.checkbox("Autoconsommation", value=True, key="show_autoconsumption_solar")
            if show_autoconsumption:
                data_to_show.append("Autoconsumption")
        
        # If both excedent and autoconsumption exist, offer to show total production
        if has_excedent and has_autoconsumption:
            show_total = st.checkbox("Production totale", value=False, key="show_total_solar")
            if show_total:
                # Add total production to dataframe if it doesn't exist
                if "Total Production" not in test2.columns:
                    test2["Total Production"] = test2["Excedent"] + test2["Autoconsumption"]
                data_to_show.append("Total Production")

    # User input for selecting time parameters based on time_range
    selected_date = None
    selected_week = None
    selected_season = None
    selected_years = st.multiselect("Sélectionnez les années à comparer", 
                                   options=test2['Year'].unique(), 
                                   default=test2['Year'].unique())

    if time_range == "Jour":
        months = [f"{i:02d} - {month}" for i, month in enumerate(["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
                                                              "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"], 1)]
        days = [f"{i:02d}" for i in range(1, 32)]
        
        col1, col2 = st.columns(2)
        with col1:
            selected_month = st.selectbox("Sélectionnez un mois", months, index=0, key="month_select_solar")
        with col2:
            selected_day = st.selectbox("Sélectionnez un jour", days, index=0, key="day_select_solar")
        
        # Option to choose between hourly and quarter-hour view
        resolution = st.radio("Résolution temporelle :", ("Horaire", "Quart d'heure"), key="day_resolution_solar", horizontal=True)
        
        selected_month_number = selected_month.split(" - ")[0]
        selected_date = pd.Timestamp(f"1900-{selected_month_number}-{selected_day}")
        
    elif time_range == "Semaine":
        selected_week = st.slider("Sélectionnez une semaine", min_value=1, max_value=52, value=1, key="week_slider_solar")
        
    elif time_range == "Saison":
        seasons = ["Hiver (Jan-Mar)", "Printemps (Avr-Juin)", "Été (Juil-Sep)", "Automne (Oct-Déc)"]
        selected_season = st.selectbox("Sélectionnez une saison", seasons, index=0, key="season_select_solar")

    # Process the data based on time_range
    if time_range == "Année":
        # Filter data for selected years
        filtered_years_data = test2[test2['Year'].isin(selected_years)]
        
        if filtered_years_data.empty:
            st.warning("Aucune donnée pour les années sélectionnées.")
            return
        
        # Sort the selected years
        selected_years_sorted = sorted(selected_years)
        
        # Dictionary to store daily data for each year
        year_data_dict = {}
        
        # Get data for each selected year with daily granularity
        for year in selected_years_sorted:
            year_data = test2[test2['Year'] == year]
            if not year_data.empty:
                year_data_dict[year] = year_data.resample('D').sum(numeric_only=True)
        
        # Create continuous timeline without gaps between non-consecutive years
        continuous_data = {}  # Store data with transformed dates
        shifted_dates_map = {}  # Map transformed dates to original dates
        
        for i, year in enumerate(selected_years_sorted):
            if year in year_data_dict:
                year_df = year_data_dict[year]
                
                # For the first year, use dates as they are
                if i == 0:
                    continuous_data[year] = year_df
                    for date in year_df.index:
                        shifted_dates_map[date] = date
                else:
                    # For subsequent years, create dates adjacent to the previous one
                    prev_year = selected_years_sorted[i-1]
                    last_date_prev_year = max(continuous_data[prev_year].index)
                    
                    # Calculate transformed dates for this year
                    transformed_dates = []
                    real_dates = []
                    
                    for idx, date in enumerate(year_df.index):
                        day_of_year = (date - pd.Timestamp(f"{year}-01-01")).days + 1
                        new_date = last_date_prev_year + pd.Timedelta(days=day_of_year)
                        
                        transformed_dates.append(new_date)
                        real_dates.append(date)
                        shifted_dates_map[new_date] = date
                    
                    transformed_df = pd.DataFrame(
                        index=transformed_dates, 
                        data=year_df.values, 
                        columns=year_df.columns
                    )
                    continuous_data[year] = transformed_df
        
        # Plot data with transformed dates
        # Keep track of which data types have been added to the legend
        legend_added = {data_col: False for data_col in data_to_show}
        
        # Define line styles for different years
        line_styles = {
            0: dict(dash="solid", width=2.5),
            1: dict(dash="solid", width=2.5),
            2: dict(dash="solid", width=2.5),
            3: dict(dash="solid", width=2.5),
        }
        
        for i, year in enumerate(selected_years_sorted):
            if year in continuous_data:
                df = continuous_data[year]
                
                # For each data series to show
                for data_col in data_to_show:
                    if data_col in df.columns:
                        # Prepare data for hover (real dates)
                        hover_dates = [shifted_dates_map.get(date, date) for date in df.index]
                        hover_text = [d.strftime('%Y-%m-%d') for d in hover_dates]
                        
                        # Determine base name and color (without year)
                        if data_col == consumption_col:
                            base_name = "Consommation"
                            color = color_map['Consumption']
                            legend_group = 'Consommation'
                        elif data_col == "Excedent":
                            base_name = "Excédent"
                            color = color_map['Excedent']
                            legend_group = 'Excédent'
                        elif data_col == "Autoconsumption":
                            base_name = "Autoconsommation"
                            color = color_map['Autoconsumption']
                            legend_group = 'Autoconsommation'
                        elif data_col == "Total Production":
                            base_name = "Production totale"
                            color = color_map['Total Production']
                            legend_group = 'Production totale'
                        else:
                            base_name = data_col
                            color = '#000000'  # Default black
                            legend_group = data_col
                        
                        # Select line style based on year index
                        line_style = line_styles[i % len(line_styles)]
                        
                        # Create hover template that includes year information
                        hover_template = f'%{{text}}<br>{base_name}: %{{y:.3f}} kWh<extra>Année: {year}</extra>'
                        
                        # Add trace for this data series
                        fig.add_trace(go.Scatter(
                            x=df.index,
                            y=df[data_col],
                            mode='lines',
                            name=base_name,
                            legendgroup=legend_group,
                            showlegend=not legend_added[data_col],
                            line=dict(color=color, **line_style),
                            hovertemplate=hover_template,
                            text=hover_text
                        ))
                        
                        # Mark this data type as added to the legend
                        legend_added[data_col] = True
        
        # Determine date range for the chart
        all_dates = []
        for year in selected_years_sorted:
            if year in continuous_data:
                all_dates.extend(continuous_data[year].index)
        
        date_min = min(all_dates)
        date_max = max(all_dates)
        total_days = (date_max - date_min).days
        
        # Create custom ticks to correctly show years
        custom_ticks = []
        custom_tick_labels = []
        
        # Optimize ticks for daily view
        if total_days <= 14:
            tick_interval = 1  # Daily
        elif total_days <= 60:
            tick_interval = 5  # Every 5 days
        elif total_days <= 120:
            tick_interval = 10  # Every 10 days
        else:
            tick_interval = 30  # Monthly
        
        current_date = date_min
        while current_date <= date_max:
            custom_ticks.append(current_date)
            real_date = shifted_dates_map.get(current_date, current_date)
            
            if total_days <= 60:
                custom_tick_labels.append(real_date.strftime("%d %b"))
            else:
                custom_tick_labels.append(real_date.strftime("%b %Y"))
            
            current_date += pd.Timedelta(days=tick_interval)
        
        # Configuration for Year view with interactive slider
        fig.update_layout(
            title='Production et consommation journalières pour les années sélectionnées', 
            xaxis_title='Date', 
            yaxis_title='kWh',
            height=600, 
            xaxis=dict(
                rangeslider=dict(
                    visible=True,
                    thickness=0.18,
                    bgcolor='rgba(13, 71, 161, 0.2)'
                ),
                type="date",
                tickvals=custom_ticks,
                ticktext=custom_tick_labels,
                tickmode='array',
                range=[date_min, date_max]
            ),
            margin=dict(l=50, r=50, t=60, b=60),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            hovermode='closest',
            uirevision="Don't change zoom on update"
        )
        
        # Configure Reset Zoom button
        fig.update_layout(
            updatemenus=[dict(
                type="buttons",
                showactive=False,
                x=0.8,
                y=1.0,
                xanchor="left",
                yanchor="bottom",
                bgcolor="rgba(240, 240, 240, 0.8)",
                bordercolor="rgba(0, 0, 0, 0.3)",
                buttons=[
                    dict(
                        label="Reset Zoom",
                        method="relayout",
                        args=[{"xaxis.range": [date_min, date_max]}]
                    )
                ]
            )]
        )
        
        # Display the chart with interactive slider without toolbar
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        # Add info bubble for usage guidance
        tooltip_info("Mode d'emploi du zoom")
        st.info("""
            **Utilisation du zoom:**
            - Sélectionnez une zone sur le graphique pour zoomer
            - Utilisez le curseur en bas pour naviguer dans les données
            - Pour revenir à la vue complète, cliquez sur "Reset Zoom" en haut à droite du graphique
        """)
        
    elif time_range == "Saison":
        season_months = {
            "Hiver (Jan-Mar)": [1, 2, 3],
            "Printemps (Avr-Juin)": [4, 5, 6],
            "Été (Juil-Sep)": [7, 8, 9],
            "Automne (Oct-Déc)": [10, 11, 12]
        }
        
        # Create subplots for each data series
        data_series = []
        for data_col in data_to_show:
            series_values = []
            for year in selected_years:
                year_data = test2[test2['Year'] == year]
                season_sums = []
                for season, months in season_months.items():
                    season_data = year_data[year_data.index.month.isin(months)]
                    if not season_data.empty:
                        season_data = season_data.resample('D').sum(numeric_only=True)
                        if data_col in season_data.columns:
                            season_sum = season_data[data_col].sum()
                            season_sums.append(season_sum)
                        else:
                            season_sums.append(0)
                
                # Determine color and name
                if data_col == consumption_col:
                    name = f"Consommation ({year})"
                    color = color_map['Consumption']
                elif data_col == "Excedent":
                    name = f"Excédent ({year})"
                    color = color_map['Excedent']
                elif data_col == "Autoconsumption":
                    name = f"Autoconsommation ({year})"
                    color = color_map['Autoconsumption']
                elif data_col == "Total Production":
                    name = f"Production totale ({year})"
                    color = color_map['Total Production']
                else:
                    name = f"{data_col} ({year})"
                    color = '#000000'  # Default black
                
                fig.add_trace(go.Bar(
                    x=list(season_months.keys()), 
                    y=season_sums, 
                    name=name, 
                    marker_color=color
                ))
                
        fig.update_layout(
            barmode='group', 
            title='Production et consommation par saison pour les années sélectionnées', 
            xaxis_title='Saison', 
            yaxis_title='kWh'
        )
        st.plotly_chart(fig)
        
    elif time_range == "Semaine":
        # Dictionary to map day numbers to names
        weekday_names = {
            0: "Lundi",
            1: "Mardi", 
            2: "Mercredi",
            3: "Jeudi",
            4: "Vendredi",
            5: "Samedi",
            6: "Dimanche"
        }
        
        # Create tick positions for the middle of each day
        tick_positions = [i * 24 + 12 for i in range(7)]  # Position at noon for each day
        tick_labels = [weekday_names[i] for i in range(7)]
        
        for year in selected_years:
            year_data = test2[test2['Year'] == year]
            week_data = year_data[year_data['Week'] == selected_week]
            
            if not week_data.empty:
                week_data = week_data.groupby([week_data.index.weekday, week_data.index.hour]).mean(numeric_only=True)
                
                # Plot each selected data series
                for data_col in data_to_show:
                    if data_col in week_data.columns:
                        # Prepare data for hover
                        hover_text = []
                        for day, hour in week_data.index:
                            hover_text.append(f"{weekday_names[day]}, {hour}:00")
                        
                        # Determine color and name
                        if data_col == consumption_col:
                            name = f"Consommation ({year})"
                            color = color_map['Consumption']
                        elif data_col == "Excedent":
                            name = f"Excédent ({year})"
                            color = color_map['Excedent']
                        elif data_col == "Autoconsumption":
                            name = f"Autoconsommation ({year})"
                            color = color_map['Autoconsumption']
                        elif data_col == "Total Production":
                            name = f"Production totale ({year})"
                            color = color_map['Total Production']
                        else:
                            name = f"{data_col} ({year})"
                            color = '#000000'  # Default black
                            
                        fig.add_trace(go.Scatter(
                            x=week_data.index.get_level_values(0) * 24 + week_data.index.get_level_values(1),
                            y=week_data[data_col],
                            mode='lines',
                            name=name,
                            line=dict(color=color),
                            hovertemplate="Jour-Heure: %{text}<br>" + name.split(" (")[0] + ": %{y:.3f} kWh<extra></extra>",
                            text=hover_text
                        ))
        
        fig.update_layout(
            title=f'Production et consommation pour la semaine {selected_week} pour les années sélectionnées',
            xaxis_title='Jour de la semaine',
            yaxis_title='kWh',
            xaxis=dict(
                tickvals=tick_positions,
                ticktext=tick_labels,
                tickmode='array'
            )
        )
        st.plotly_chart(fig)
        
    elif time_range == "Jour":
        for year in selected_years:
            year_data = test2[test2['Year'] == year]
            day_data = year_data[year_data.index.strftime('%m-%d') == selected_date.strftime('%m-%d')]
            
            if not day_data.empty:
                for data_col in data_to_show:
                    if data_col not in day_data.columns:
                        continue
                        
                    if resolution == "Horaire":
                        # Hourly view
                        # Resample to 15 minutes
                        day_data_resampled = day_data.resample('15T').sum(numeric_only=True)
                        
                        # Create a new DataFrame to store hourly sums
                        hourly_data = pd.DataFrame(index=range(0, 24), columns=[data_col])
                        hourly_data.index.name = 'Hour'
                        
                        # Calculate sums for each hour from 0 to 22 (00:15-23:00)
                        for hour in range(0, 23):
                            start_time = f'{hour:02d}:15:00'
                            end_time = f'{hour+1:02d}:00:00'
                            hourly_data.loc[hour, data_col] = day_data_resampled.between_time(start_time, end_time)[data_col].sum()
                        
                        # Special case for hour 23 (23:15-00:00)
                        midnight_data = day_data_resampled.between_time('23:15', '00:00').sum(numeric_only=True)
                        if data_col in midnight_data:
                            hourly_data.loc[23, data_col] = midnight_data[data_col]
                        
                        # Determine color and name
                        if data_col == consumption_col:
                            name = f"Consommation ({year})"
                            color = color_map['Consumption']
                        elif data_col == "Excedent":
                            name = f"Excédent ({year})"
                            color = color_map['Excedent']
                        elif data_col == "Autoconsumption":
                            name = f"Autoconsommation ({year})"
                            color = color_map['Autoconsumption']
                        elif data_col == "Total Production":
                            name = f"Production totale ({year})"
                            color = color_map['Total Production']
                        else:
                            name = f"{data_col} ({year})"
                            color = '#000000'  # Default black
                            
                        fig.add_trace(go.Scatter(
                            x=hourly_data.index,
                            y=hourly_data[data_col],
                            mode='lines',
                            name=name,
                            line=dict(color=color),
                            hovertemplate="Heure: %{x}:00<br>" + name.split(" (")[0] + ": %{y:.3f} kWh<extra></extra>"
                        ))
                        
                    else:  # "Quart d'heure"
                        # Quarter-hour view
                        # Resample to quarter hour and format data for display
                        quarter_data = day_data.resample('15T').sum(numeric_only=True)
                        
                        # Prepare X axis for quarter hour display (starting at 00:15)
                        time_labels = []
                        # Add labels from 00:15 to 23:45
                        for i in range(0, 24):
                            for j in [15, 30, 45]:
                                time_labels.append(f"{i:02d}:{j:02d}")
                            if i < 23:  # Add full hours except 00:00 which will be at the end
                                time_labels.append(f"{i+1:02d}:00")
                        # Add 00:00 at the end as 24:00
                        time_labels.append("24:00")
                        
                        # Create sequential index to correctly plot data
                        quarter_index = list(range(len(time_labels)))
                        
                        # Prepare data for display
                        quarter_values = []
                        hover_texts = []
                        
                        for i, label in enumerate(time_labels):
                            if label == "24:00":
                                # Get 00:00 value for next day
                                next_day = selected_date
                                next_day_str = next_day.strftime('%m-%d')
                                next_day_data = year_data[year_data.index.strftime('%m-%d') == next_day_str]
                                if not next_day_data.empty:
                                    midnight_data = next_day_data[next_day_data.index.strftime('%H:%M') == '00:00']
                                    if not midnight_data.empty and data_col in midnight_data.columns:
                                        quarter_values.append(midnight_data[data_col].iloc[0])
                                        hover_texts.append("00:00 (fin de journée)")
                                    else:
                                        quarter_values.append(0)
                                        hover_texts.append("00:00 (fin de journée)")
                                else:
                                    quarter_values.append(0)
                                    hover_texts.append("00:00 (fin de journée)")
                            else:
                                # For all other quarter hours
                                hour, minute = map(int, label.split(':'))
                                time_str = f"{hour:02d}:{minute:02d}"
                                # Find data corresponding to this quarter hour
                                time_data = quarter_data[quarter_data.index.strftime('%H:%M') == time_str]
                                
                                if not time_data.empty and data_col in time_data.columns:
                                    quarter_values.append(time_data[data_col].iloc[0])
                                    hover_texts.append(f"{time_str}")
                                else:
                                    quarter_values.append(0)
                                    hover_texts.append(f"{time_str}")
                        
                        # Determine color and name
                        if data_col == consumption_col:
                            name = f"Consommation ({year})"
                            color = color_map['Consumption']
                        elif data_col == "Excedent":
                            name = f"Excédent ({year})"
                            color = color_map['Excedent']
                        elif data_col == "Autoconsumption":
                            name = f"Autoconsommation ({year})"
                            color = color_map['Autoconsumption']
                        elif data_col == "Total Production":
                            name = f"Production totale ({year})"
                            color = color_map['Total Production']
                        else:
                            name = f"{data_col} ({year})"
                            color = '#000000'  # Default black
                            
                        # Plot data
                        fig.add_trace(go.Scatter(
                            x=quarter_index,
                            y=quarter_values,
                            mode='lines',
                            name=name,
                            line=dict(color=color),
                            hovertemplate="Heure: %{text}<br>" + name.split(" (")[0] + ": %{y:.3f} kWh<extra></extra>",
                            text=hover_texts
                        ))
        
        # Configuration based on resolution
        if resolution == "Horaire":
            fig.update_layout(
                title=f'Production et consommation du {selected_date.strftime("%d %B")} par heure pour les années sélectionnées',
                xaxis_title='Heure de la journée',
                yaxis_title='kWh',
                xaxis=dict(
                    tickmode='array',
                    tickvals=list(range(0, 24)),
                    ticktext=[f"{h:02d}:00" for h in range(0, 24)]
                )
            )
        else:  # "Quart d'heure"
            # Show only complete hours to avoid clutter
            tick_positions = []
            tick_labels = []
            # Tick positions for each hour (01:00 to 24:00)
            for i in range(24):
                pos = i * 4  # 4 quarter hours per hour
                if i > 0:  # We shift because we start at 00:15
                    tick_positions.append(pos - 1)
                    tick_labels.append(f"{i:02d}:00")
            
            fig.update_layout(
                title=f'Production et consommation du {selected_date.strftime("%d %B")} par quart d\'heure pour les années sélectionnées',
                xaxis_title='Heure de la journée',
                yaxis_title='kWh',
                xaxis=dict(
                    tickmode='array',
                    tickvals=tick_positions,
                    ticktext=tick_labels,
                    range=[0, len(quarter_index)-1]
                )
            )
        
        # Display the chart
        st.plotly_chart(fig)
        
        # Display explanatory note adapted to selected resolution
        if resolution == "Horaire":
            st.info("Note : Les valeurs par heure correspondent à la somme de quatre quart d'heure. "
                   "Par exemple, la valeur pour 00:00 correspond à la consommation/production entre 00:15 et 01:00, "
                   "moyennée pour tous les jours identiques de l'année.")
        else:
            st.info("Note : Les données par quart d'heure montrent la consommation/production détaillée "
                   "pour chaque période de 15 minutes, moyennée pour tous les jours identiques (même date) "
                   "de l'année où les données sont disponibles.")

    # Add description of solar data visualizations
    st.markdown("---")
    with st.expander("À propos des données solaires", expanded=False):
        st.markdown("""
        ### Comprendre vos données solaires
        
        **Excédent (réinjecté)** : Représente l'énergie solaire produite mais non consommée directement par votre logement, 
        et donc réinjectée dans le réseau.
        
        **Autoconsommation** : Représente l'énergie solaire que vous avez produite et consommée directement, 
        sans passer par le réseau.
        
        **Production totale** : Somme de l'excédent réinjecté et de l'autoconsommation, représentant la totalité 
        de l'énergie produite par vos panneaux solaires.
        
        **Consommation** : Votre consommation électrique totale, incluant l'électricité du réseau et l'autoconsommation.
        
        ### Optimiser votre installation solaire
        
        Pour maximiser les bénéfices de votre installation solaire, essayez de :
        
        1. **Faire correspondre votre consommation aux heures de production** : Utilisez vos appareils énergivores 
           (lave-vaisselle, machine à laver, etc.) pendant les périodes de forte production solaire.
        
        2. **Surveiller votre taux d'autoconsommation** : Plus vous consommez directement votre production solaire, 
           plus votre installation est rentable.
        
        3. **Analyser les variations saisonnières** : Comprenez comment votre production varie au fil des saisons 
           pour adapter vos habitudes de consommation.
        """)

    # Check if autoconsumption data exists but is mostly zeros
    if has_autoconsumption and test2["Autoconsumption"].sum() < 0.1 * test2[consumption_col].sum():
        st.warning("""
        **Note importante** : Les valeurs d'autoconsommation semblent très faibles par rapport à votre consommation totale. 
        Si vous possédez des panneaux solaires, vérifiez que vos données d'autoconsommation sont correctement mesurées.
        """)
