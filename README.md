# 🚲 Chicago Bike Crash Dashboard

An interactive cartogram visualizing bike accidents across Chicago community areas.  
Built with [Plotly Dash](https://dash.plotly.com/), this dashboard highlights crash frequency, severity, top causes, and bikability for each neighborhood.

🔗 **Live App**: [https://chicago-bike-dashboard.onrender.com](https://chicago-bike-dashboard.onrender.com)

---

## 🧭 Features

- 📊 Visualizes crash frequency and serious injury rate by community area  
- 📍 Hoverable, clickable map tiles with abbreviations and risk bars  
- 🛣️ Bike infrastructure breakdown: protected, buffered, shared lanes  
- 📌 Top 5 crash causes per area  
- 🩸 Detailed injury breakdown  
- 🚴 Bikeability scores from 0 to 5  

---

## 📦 Tech Stack

- `Dash` + `Plotly` – interactive web UI and graphics  
- `Pandas`, `GeoPandas`, `Shapely` – spatial data processing  
- `Gunicorn` – production WSGI server  
- `Docker` – containerized deployment

---

## 🚀 Deployment

This app is deployed via [Render](https://render.com) using a `Dockerfile`.

To deploy yourself:

```bash
# Clone repo
git clone https://github.com/YOUR_USERNAME/chicago-bike-dashboard.git
cd chicago-bike-dashboard

# Build and run locally
docker build -t dash-app .
docker run -p 8000:8000 dash-app
```

---

## 🗂️ Data Sources

- **Crash data**: Chicago Open Data Portal  
- **Community areas**: U.S. Census / TIGER  
- **Bike lanes**: Chicago Department of Transportation (CDOT)  
- **Population & road length**: Derived from Census geometries  

---

## 📚 Blog Post

Read more about this project and the methodology here:  
📝 _[Link to Medium post]_ (optional)

---

## 🧑‍💻 Author

**Samvardhan Vishnoi**  
Ph.D. candidate in Physics @ Northwestern University  
[LinkedIn](https://www.linkedin.com/in/samvardhan-vishnoi) • [Medium](https://medium.com/@s-vishnoi)

[• [Portfolio](https://your-vercel-site.vercel.app)]:#

---

## 📝 License

This project is open-source and free to use under the [MIT License](LICENSE).
