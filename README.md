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
- **Deployment:** Hosted on **Cloudflare Pages**, with automated builds to fetch live data.

---

## Quickstart (Running Locally)

This folder is a self-contained static snapshot. To view the map with the currently checked-in dataset:

```bash
# 1. Regenerate the JSON data payload for the browser
python3 generate_atlas_data.py

# 2. Serve the directory locally
python3 -m http.server 8090
```
Then open: [http://127.0.0.1:8090/](http://127.0.0.1:8090/)

### Build a shareable single-file export
If you want to email the map or distribute it entirely offline:
```bash
python3 build_shareable_html.py
```
This writes `chicago-bikeability-atlas.html`, an all-in-one file containing the HTML, CSS, JS, and Base64-encoded assets that can be opened directly in any browser.

---

## Updates / Live Rebuild Flow

Use this flow to refresh the crash data and population numbers directly from the City of Chicago APIs. *(Internet access required).*

```bash
# 1. Pull the latest crash data from Socrata
python3 refresh_live_crashes.py

# 2. Update population counts from CMAP
python3 refresh_population.py

# 3. Compile the new datasets
python3 generate_atlas_data.py

# 4. (Optional) Re-bundle the shareable HTML
python3 build_shareable_html.py
```

### Optional: Road Basemap Refresh
To refresh the OpenStreetMap Chicago road centerlines (used for the Google-ish road basemap underneath the bike-lane overlay and for crash-marker hover street names):

```bash
python3 fetch_osm_roads.py
python3 generate_atlas_data.py
python3 build_shareable_html.py
```

### Deployment
This map is designed to be easily deployed on **Cloudflare Pages**. 
To automate the data fetching during deployment, set your Cloudflare Pages build command to:
`python3 refresh_live_crashes.py && python3 refresh_population.py && python3 generate_atlas_data.py`

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
