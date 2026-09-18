# Qualifying Grocery Store Classification Rubric (MVP)
#
# Purpose
# -------
# Define which stores count as "qualifying grocery stores" for Detroit
# 15-minute walking access analysis. This file is the human-readable
# source of truth. Revise it when the classification policy changes.
#
# Important: what V1 does and does not claim
# -----------------------------------------
# V1 "qualifying" means minimum grocery assortment for a normal shopping trip.
#
# It does NOT mean the store is:
#   - good quality
#   - fairly priced / affordable
#   - culturally appropriate
#   - clean, well-stocked, or consistently open
#
# Detroit has many stores that meet a bare-minimum assortment bar while still
# being overpriced, low-quality, or otherwise inadequate. Those stores can
# still qualify under the V1 assortment screen. Treat the headline access
# metric as geographic assortment access — not food security, and not
# "access to good groceries."
#
# Core assortment standard (V1)
# -----------------------------
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
# co-ops, and ethnic/specialty grocers qualify on assortment when they can
# reasonably support a full grocery trip.
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
# Planned / optional adequacy fields (not scored automatically in V1)
# -------------------------------------------------------------------
# These columns exist so reviewers can later separate "technically a grocery"
# from "a grocery people can actually rely on":
#
#   adequacy_tier:
#     - assortment_only  → meets V1 assortment bar; quality/price not endorsed
#     - adequate         → reviewer judges assortment + basic quality/usability OK
#     - preferred        → stronger option on quality, price, or community value
#     - excluded         → does not qualify
#
#   price_concern: unknown | yes | no
#   quality_concern: unknown | yes | no
#   reviewer_notes: free text from human review
#
# Do not invent numeric quality or price scores in V1.
#
# Borderline cases
# ----------------
# Review manually. Document the decision in the `notes` / `reviewer_notes` fields.
# Examples:
#   - Large produce markets with staples and protein → usually qualify on assortment
#   - Small corner stores with a produce cooler but mostly packaged snacks → exclude
#   - Warehouse clubs requiring membership → document; MVP generally excludes
#     unless clearly used as neighborhood grocery access
#   - Full supermarket known locally as chronically overpriced or poor produce
#     → may still qualify on assortment; set price_concern/quality_concern and
#       keep adequacy_tier=assortment_only until a stricter policy is adopted
#
# Process (V1 / V1.1)
# ------------------
# 1. Prefer Detroit Food Map Initiative full-line grocery master list
#    (DetroitData, ground-truthed) as the primary qualifying set.
# 2. Optionally retain OpenStreetMap supermarket/grocery candidates for
#    comparison, but do not let OSM alone drive the headline set.
# 3. Restrict to City of Detroit (with optional near-boundary buffer later).
# 4. Record qualifies / store_type / adequacy / NEMS placeholder fields /
#    DFM attributes / notes / last_verified in
#    data/manual/qualifying_grocers.csv
# 5. Do not invent NEMS scores. Leave nems_* blank with nems_status=pending
#    until partnership or published audit scores are available.
# 6. Do not use automated AI classification in V1.
#
# Note: OSM tags are a starting point, not ground truth. DFM full-line status
# is stronger evidence of assortment. Field verification of quality and price
# (NEMS / Great Grocer) should refine adequacy before policy use.
#
# Fields in qualifying_grocers.csv
# --------------------------------
# id, name, address, latitude, longitude, source, qualifies, store_type,
# adequacy_tier, price_concern, quality_concern,
# nems_availability, nems_price, nems_quality, nems_total, nems_survey_year, nems_status,
# dfm_community_score, snap, wic, green_grocer, ggp18, ggp21, sq_ft_thousands,
# notes, reviewer_notes, last_verified
#
# Geographic note
# ---------------
# Primary statistics use City of Detroit boundaries. The data model allows
# stores outside the city (within a buffer) to be added later if Detroit
# residents can walk to them. For MVP, include_outside_city_stores is false
# unless a store is explicitly marked and configuration is updated.
