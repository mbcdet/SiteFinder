# First Validation — Representative Sample

Goal: learn as much as possible from a tiny sample before any larger matrix. Three runs:

| District | Category | Bezirk |
|---|---|---|
| 7 | dentist | Neubau |
| 7 | hair_salon | Neubau |
| 1 | restaurant | Innere Stadt |

## Run it (local — needs network)

```bash
pip install -e ".[dev]" && pytest          # green suite first
sitefinder run -d 7 -c dentist
sitefinder run -d 7 -c hair_salon
sitefinder run -d 1 -c restaurant
```

Outputs land in `results/<category>/district_<NN>/{leads.csv,report.txt}`.
Quick comparison of the three reports:

```bash
grep -H "Potential Leads\|Persisted" results/*/district_*/report.txt
```

## Sanity-check recall directly in Overpass Turbo (optional)

Paste any of these at https://overpass-turbo.eu to eyeball raw coverage independent of the tool —
these are the exact queries the tool sends:

```
# dentist / D7 (Neubau)
[out:json][timeout:60];
area["boundary"="administrative"]["admin_level"="9"]["name"="Neubau"]->.searchArea;
( nwr["amenity"="dentist"](area.searchArea); nwr["healthcare"="dentist"](area.searchArea); );
out center tags;

# hair_salon / D7 (Neubau)
[out:json][timeout:60];
area["boundary"="administrative"]["admin_level"="9"]["name"="Neubau"]->.searchArea;
( nwr["shop"="hairdresser"](area.searchArea); );
out center tags;

# restaurant / D1 (Innere Stadt)
[out:json][timeout:60];
area["boundary"="administrative"]["admin_level"="9"]["name"="Innere Stadt"]->.searchArea;
( nwr["amenity"="restaurant"](area.searchArea); );
out center tags;
```

## What to inspect (the learning, not the count)

1. **Coverage vs reality** — pick a street in Neubau you know; are the salons/dentists there present?
   Missing ones quantify the *residual* OSM gap after the boundary fix (decides if directory plugins
   are ever needed).
2. **Classification accuracy** — open ~10 `no_website` / `social_only` rows; are they truly without a
   real site? (False positives = wasted visits.)
3. **Noise** — chains/franchises, duplicates, anything that isn't a real local SMB prospect.
4. **Lead density** — does each run yield enough genuine prospects to justify a visit round? Compare
   the three categories.

Bring the three `report.txt` summaries (and any surprises from #1–#2) back and we'll decide together
whether a larger matrix or a different strategy is warranted.

## Commit this improvement (local — sandbox can't run git; see note)

```bash
git add sitefinder/collector/osm_source.py tests/unit/test_osm_source.py VALIDATION_SAMPLE.md
git commit -m "feat(discovery): guard boundary area and backfill district postcode

Add boundary=administrative to the Bezirk area selector to avoid name
collisions; backfill postal_code from the searched district when the OSM
element lacks an addr:postcode tag; broaden social tag keys."
pytest && git push origin main
```
