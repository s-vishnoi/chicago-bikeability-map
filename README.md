# Chicago Bikeability Atlas

This project maps biking safety and accessibility across Chicago community areas. Users can explore crash statistics and availability of biking infrastructure by Community area.

As an avid biker on the streets of Chicago, I wanted to build a data-powered real-time map of biking safety across different Chicago neighborhoods. My map pulls data from various sources on city scale metrics, infrastructure, historical crash data, and builds a comprehensive Bikeability score for each neighborhood for quick comparison. Avid users can also deep dive on individual crash locations and causes to identify persistent points of harm across the city network.

A custom cartogram-style layout improves accessibility and starkly highlights city-wide inequity.

🔗 **[Interactive Map](https://www.vishnoi.site/bikeability)**

---

## Data Sources
- **Crash data:** City of Chicago Socrata Traffic Crashes API
- **Community data:** CMAP 2025 Community Data Snapshots & U.S. Census
- **Road network & Basemaps:** OpenStreetMap (Overpass API)
- **Bike lanes:** Chicago Department of Transportation (CDOT)

## Features
- **Interactive Cartogram:** A custom grid map of Chicago’s community areas.
- **Crashes:** See and compare total bike crashes with leading causes across communities since 2018.
- **Injury:** Rates of severe (fatal, incapacitating), and non-severe injuries.
- **Infrastructure:** See miles of bike lanes per community by type—Protected, Neighborhood, Buffered, Bike (Painted), Shared. Compare to total road miles in the area.
- **Network:** See ease of lane availability for bikers in the community forming a bike network.
- **Bikeability:** Final community rank (1-5), based on Infrastructure and Network scores.

## Tech Stack
This new version of the Atlas has been entirely rewritten to be **100% dependency-free** and highly portable. 
- **Frontend:** Pure HTML, Vanilla JavaScript, and CSS (No frameworks!)
- **Data Pipeline:** Python 3 (Strictly using the Standard Library—no `pandas` or `geopandas` required).
- **Deployment:** Fully automated via **GitHub Actions** and served on **GitHub Pages**.

---

## Deployment & Automation

This project is deployed using **GitHub Pages**. 
A GitHub Actions workflow (`.github/workflows/deploy.yml`) is set up to fully automate this map.

### Live Rebuild Flow
Every Sunday at midnight (or manually triggered), GitHub Actions automatically spins up a worker to run the following sequence:

1. **`refresh_live_crashes.py`**: Pulls current pedalcyclist crash records from the City of Chicago Socrata Traffic Crashes API.
2. **`refresh_population.py`**: Pulls latest population data from CMAP.
3. **`fetch_osm_roads.py`**: Refreshes OpenStreetMap Chicago road centerlines.
4. **`generate_atlas_data.py`**: Compiles the fresh data into a new map dataset (`atlas-data.json`).
5. **`build_shareable_html.py`**: Bundles the application into a single HTML file.

After generating the new datasets, the workflow commits the changes back to the repository and deploys the fresh map to GitHub Pages. You never have to build or run this locally!

---

## Article
Read more about my motivation for this project here: 📝 [Blog](https://medium.com/@s-vishnoi/riding-upstream-the-windy-city-113a6a8415a9)

## Author
**Samvardhan Vishnoi**
Ph.D. candidate in Physics @ Northwestern University

[LinkedIn](https://www.linkedin.com/in/samvardhan-vishnoi) • [Medium](https://medium.com/@s-vishnoi) • [Portfolio](https://www.vishnoi.site)

## Credits
I'd like to thank Ted Whalen (@tewhalen) for the initial draft of the Chicago cartogram grid.

## License
This project is open-source and free to use under the [MIT License](LICENSE).
