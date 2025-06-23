# 🚲 Chicago Bikeability Dashboard

An interactive cartogram visualizing bike traffic crashes across Chicago community areas.

This dashboard highlights crash frequency, common causes, and severity for each community area. It also maps biking infrastructure in each area and aggregates it into a Bikeability score (loosely defined). Users can glean quick insights into biking safety in Chicago, helping to identify areas needing improvement. 
🔗 **Live App**: [https://chicago-bike-dashboard.onrender.com](https://chicago-bike-dashboard.onrender.com)

---

## 🧭 Features

- 📊 Visualizes crash frequency and severe injury rate by community area  
- 📍 Interactive cartogram
- 🛣️ Bike infrastructure breakdown: Protected, Buffered, Neighborhood, Bike (Painted), Shared
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
📝 _[Link to Medium post]_

---

## 🧑‍💻 Author

**Samvardhan Vishnoi**  
Ph.D. candidate in Physics @ Northwestern University  
[LinkedIn](https://www.linkedin.com/in/samvardhan-vishnoi) • [Medium](https://medium.com/@s-vishnoi)

[• [Portfolio](https://your-vercel-site.vercel.app)]:#

---

## 🤝 Credits  
I'd like to thank Ted Whalen (Github @tewhalen) for initial structuring grid for Chicago cartogram that I adapted for use here.


## 📝 License

This project is open-source and free to use under the [MIT License](LICENSE).
