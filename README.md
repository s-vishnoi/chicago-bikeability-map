# 🚲 Chicago Bikeability Dashboard

An interactive cartogram visualizing bike traffic crashes across Chicago community areas.

This tool highlights crash counts, causes, and severity for each community area. It also maps biking infrastructure and network in each area and aggregates them into a custom Bikeability score. Users can glean quick insights and help identify areas for improvement.

🔗 [Live App](https://www.vishnoi.site/bikeability)

---

 
## Features

- 📍 **Interactive Cartogram** of Chicago’s community areas  
- 📊 **Crash & Injury Visualization**: total crashes with top causes
- 🩸 **Injury Severity Breakdown**: rates of severe (fatal, incapacitating), and non-severe injuries. 
- 🛣️ **Infrastructure Breakdown** by bike lane type: Protected, Neighborhood, Buffered, Bike (Painted), Shared 
- 🌐 **Network Map** to visualize bike lane connectivity and coverage
- 🚴 **Bikeability Rank** from 0 to 5, based on custom Infrastructure and Network Scores.   

---

## Tech Stack

- `Dash` + `Plotly` – interactive web UI
- `Pandas`, `GeoPandas`, `Shapely` – spatial data processing   
- `Docker` – containerized deployment

---

## Deployment

This app is deployed via [Render](https://render.com) using a `Dockerfile`.

To deploy yourself:

```bash
# Clone repo
git clone https://github.com/s-vishnoi/chicago-bikeability-dashboard.git
cd chicago-bikeability-dashboard

# Build and run locally
docker build -t dash-app .
docker run -p 8000:8000 dash-app
```

---

## Data Sources

- **Crash data**: Chicago Open Data Portal  
- **Community areas**: U.S. Census
- **Bike lanes**: Chicago Department of Transportation (CDOT)  
- **Road length**: Derived from Census geometries  

---

## Article

Read more about this project and the methodology here:  
📝 _[Link to Medium post]_

---

## Author

**Samvardhan Vishnoi**  
Ph.D. candidate in Physics @ Northwestern University 


[LinkedIn](https://www.linkedin.com/in/samvardhan-vishnoi) • [Medium](https://medium.com/@s-vishnoi) • [Portfolio](https://www.vishnoi.site)

---

## Credits  
I'd like to thank Ted Whalen (@tewhalen) for initial draft of Chicago cartogram grid. 


## License

This project is open-source and free to use under the [MIT License](LICENSE).
