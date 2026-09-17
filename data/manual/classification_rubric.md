# Qualifying Grocery Store Classification Rubric (MVP)
#
# Purpose
# -------
# Define which stores count as "qualifying grocery stores" for Detroit
# 15-minute walking access analysis. This file is the human-readable
# source of truth. Revise it when the classification policy changes.
#
# Core standard
# -------------
# A qualifying grocery store should provide meaningful access to a normal
# household grocery trip, including most of the following:
#
#   - fresh produce (fruit and vegetables)
#   - meat, seafood, eggs, beans, or other substantial protein options
#   - dairy and/or dairy substitutes
#   - grains and staple foods (bread, rice, pasta, cereal)
#   - frozen foods
#   - basic household grocery needs (cooking oil, spices, cleaning basics)
#
# The store does not need to be a national chain. Independent markets,
# co-ops, and ethnic/specialty grocers qualify when they can reasonably
# support a full grocery trip.
#
# Explicit exclusions (MVP)
# -------------------------
# Exclude businesses that are primarily:
#
#   - liquor stores
#   - gas stations
#   - convenience stores
#   - pharmacies
#   - dollar stores with only limited food selection
#   - specialty shops that cannot reasonably support a normal grocery trip
#     (e.g., only bakery, only butcher with no staples, only candy/snacks)
#
# Borderline cases
# ----------------
# Review manually. Document the decision in the `notes` field.
# Examples:
#   - Large produce markets with staples and protein → usually qualify
#   - Small corner stores with a produce cooler but mostly packaged snacks → exclude
#   - Warehouse clubs requiring membership → document; MVP generally excludes
#     unless clearly used as neighborhood grocery access
#
# Process (V1)
# ------------
# 1. Assemble candidates from OpenStreetMap (shop=supermarket / grocery) and
#    optional SNAP / business lists.
# 2. Restrict to City of Detroit (with optional near-boundary buffer later).
# 3. Manually screen by store name and tag against this rubric (exclude liquor,
#    convenience, pharmacy, warehouse clubs, etc.).
# 4. Record qualifies / store_type / notes / last_verified in
#    data/manual/qualifying_grocers.csv
# 5. Do not use automated AI classification in V1.
#
# Note: OSM tags are a starting point, not ground truth. Coordinates from OSM
# are preferred over geocoded guesses when available. Field verification should
# refine the list before policy use.
#
# Fields in qualifying_grocers.csv
# --------------------------------
# id, name, address, latitude, longitude, source, qualifies, store_type, notes, last_verified
#
# Geographic note
# ---------------
# Primary statistics use City of Detroit boundaries. The data model allows
# stores outside the city (within a buffer) to be added later if Detroit
# residents can walk to them. For MVP, include_outside_city_stores is false
# unless a store is explicitly marked and configuration is updated.
