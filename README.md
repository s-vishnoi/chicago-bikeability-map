# Chicago Bikeability Map

An interactive cartogram visualizing bike traffic crashes and infrastructure across Chicago community areas.

This tool highlights crash counts, causes, and severity for each community area. It also scores biking infrastructure and network in each area and aggregates them into a custom Bikeability rank. Users can glean city-wide insights and help identify areas for improvement.

🔗 [Live App](https://www.vishnoi.site/bikeability)

---

 
## Features


- **Interactive Cartogram** of Chicago’s community areas  
- **Crashes**: See and compare total bike crashes with leading causes across communities since 2018. 
- **Injury**: rates of severe (fatal, incapacitating), and non-severe injuries.
- **Infrastructure**: See miles of bike lanes per community by type- Protected, Neighborhood, Buffered, Bike (Painted), Shared. Compare to total road miles in the area. 
- **Network**: See ease of lane availability for bikers in the community (see diagram below) forming a bike network. 
- **Bikeability:** Final community rank (1-5), based on Infrastructure and Network scores.   

<img width="876" height="441" alt="Screenshot 2025-07-10 at 3 38 30 PM" src="https://github.com/user-attachments/assets/9af744ea-4eda-4bc2-bcc7-f1aeee0745c0" />


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
