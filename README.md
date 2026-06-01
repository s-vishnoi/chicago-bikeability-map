# Chicago Bikeability Map 

I bike a lot..like a LOT. Fixed gear 42:16 carbon steel frame racing through corners. 

Me and some friends were wanted a live feed of bike crashes across the city, so i made this map. 

You can see every crash involving a bicyclist, where it happened, why it happened, and how badly they were hurt. Perhaps you can dive into your community metrics to identify deeper patterns based on your local knowledge. 

The vision of this project is to bring the information that lives in .csv files ALIVE and ACCESSIBLE. 

I hope the biker community finds it easy to read, feel free to dm me suggestions!

A lot of thought was put into the cartogram design, and I'd like to thank @tedwhalen for the first neighborhood positions. 

You can read deeper about this project motivation+workflow [here](https://medium.com/@s-vishnoi/riding-upstream-the-windy-city-113a6a8415a9)

---

## Data Sources
- **Crash data:** City of Chicago Socrata Traffic Crashes API
- **Community data:** CMAP 2025 Community Data Snapshots & U.S. Census
- **Road network & Basemaps:** OpenStreetMap (Overpass API)
- **Bike lanes:** Chicago Department of Transportation (CDOT)

## Features
- **Interactive Cartogram:** A custom grid cartomap of Chicago’s community areas.
- **Infrastructure:** bike lanes per community by type—Protected, Neighborhood, Buffered, Bike (Painted), Shared
- **Crashes:** See and compare total bike crashes with leading causes across communities since 2018.
- **Injury Risk:** Rates of severe (fatal, incapacitating), and non-severe injuries.
- **Bikeability:** community stars (1-5), based on a custom internal bikeability score. 

## Tech Stack
This new version of the Atlas has been entirely rewritten to be **100% dependency-free** and highly portable. 
- **Frontend:** HTML, Vanilla JavaScript, and CSS (No frameworks!)
- **Deployment:** **GitHub Actions** served on **GitHub Pages**.

### Live Rebuild Flow
Every Sunday at midnight (or manually triggered), GitHub Actions automatically spins up a worker to run the following sequence:

1. **`refresh_live_crashes.py`**: Pulls current pedalcyclist crash records from the City of Chicago Socrata Traffic Crashes API.
2. **`refresh_population.py`**: Pulls latest population data from CMAP.
3. **`fetch_osm_roads.py`**: Refreshes OpenStreetMap Chicago road centerlines.
4. **`generate_atlas_data.py`**: Compiles the fresh data into a new map dataset (`atlas-data.json`).
5. **`build_shareable_html.py`**: Bundles the application into a single HTML file.


After generating the new datasets, the workflow commits the changes back to the repository and deploys the fresh map to GitHub Pages. You never have to build or run this locally!

---

## Author
**Samvardhan Vishnoi**
Ph.D. candidate in Physics @ Northwestern University

[LinkedIn](https://www.linkedin.com/in/samvardhan-vishnoi) • [Medium](https://medium.com/@s-vishnoi) • [Portfolio](https://www.vishnoi.site)

## License
This project is open-source and free to use under the [MIT License](LICENSE).
