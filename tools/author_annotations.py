"""Serialize statically authored image observations; this script does not review them.

This scorer-only authoring source contains answers; adapters must never import it.
Coordinates below refer to the saved preview image, then normalize to the page. The
second visual pass was performed separately and is recorded in the annotation data;
running this script does not perform or verify that pass.
"""
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RUNTIME, REFERENCES = [], []
if __name__ == "__main__" and (ROOT / "data/evaluation-freeze.json").exists():
    raise SystemExit("Refusing to run annotation authoring after the evaluation freeze; use a versioned revision.")


def add(page_id, printed, text_bounds, text, fields, notes=""):
    source_id, position = page_id.split("-p")
    manifest = json.loads((ROOT / "data/manifest.json").read_text(encoding="utf-8"))
    source = next(s for s in manifest["sources"] if s["source_id"] == source_id)
    number = int(position)
    split = "development" if number in source["development_pdf_pages"] else "evaluation"
    with Image.open(ROOT / "data/previews" / f"{page_id}.png") as image:
        width, height = image.size
    def bounds(box):
        return [round(box[0]/width, 7), round(box[1]/height, 7),
                round(box[2]/width, 7), round(box[3]/height, 7)]
    runtime = dict(page_id=page_id, source_id=source_id, source_sha256=source["sha256"],
                   pdf_page=number, printed_page_label=printed, split=split,
                   text_region={"region_id": page_id+"-text", "bounds": bounds(text_bounds)},
                   targets=[])
    reference = dict(page_id=page_id, text=text, text_evaluable=True,
                     verification="second_visual_pass_same_annotator", annotation_notes=notes,
                     targets=[])
    for index, (box, raw, row, column, period, unit) in enumerate(fields, 1):
        target_id = f"{page_id}-f{index}"
        runtime["targets"].append(dict(target_id=target_id, bounds=bounds(box),
            data_type="decimal_or_unavailable", row_label=row, column_label=column,
            period_label=period, unit_label=unit, supplied_context=True,
            withheld_context=[]))
        reference["targets"].append(dict(target_id=target_id, raw_value=raw,
            normalized_value=raw.replace(",", "") if raw is not None else None,
            expected_kind="number" if raw is not None else "unavailable",
            evaluable=True, markers=[] if raw is not None else ["dot_leader_no_value"],
            verification="second_visual_pass_same_annotator"))
    if len(fields) != 4:
        raise ValueError(f"Expected four target fields for {page_id}; received {len(fields)}")
    RUNTIME.append(runtime)
    REFERENCES.append(reference)


add("S1-p001", "", (747, 673, 1310, 862),
    "School enrollment rates continued to rank high for the compulsory attendance ages (7 to 17) and especially high for ages 7 to 13. About 99 percent of persons 7 to 13 were enrolled in school. Similar enrollment rates were reported for white and Negro persons in this age group. The school enrollment rates of children 3 and 4 years old almost doubled over the past 5 years. In",
    [((822,1091,894,1117),"60,357","Total enrolled, 3 to 34 years old","1970","October 1970","thousands of persons"),
     ((980,1091,1052,1117),"54,700","Total enrolled, 3 to 34 years old","1965","October 1965","thousands of persons"),
     ((830,1144,894,1170),"1,096","Nursery","1970","October 1970","thousands of persons"),
     ((1010,1144,1052,1170),"520","Nursery","1965","October 1965","thousands of persons")],
    "Text is the complete right-column passage ending at the page continuation; fewer than 80 words available in this region. Historical racial terminology is transcribed as printed, not endorsed.")

add("S1-p002", "2", (24,72,639,325),
    "1965, 886,000 children 3 and 4 years old, or 11 percent of those in this age group, were enrolled in nursery school or kindergarten. In 1970, this figure had in- creased to 1.5 million or 21 percent of the age group. In 1965 the number of college students was 5.7 million but in 1970 there were 7.4 million college students, an increase of 31 percent. Among those 18 to 24 years old, 4.5 million, or 24 percent of the age group, were enrolled in college in 1965, compared with 5.8 million, or 26 percent of the age group, in 1970.",
    [((464,991,540,1016),"60,357","Total enrolled","1970, All races","October 1970","thousands of persons"),
     ((570,991,648,1016),"51,719","Total enrolled","1970, White","October 1970","thousands of persons"),
     ((475,1023,540,1048),"1,096","Nursery","1970, All races","October 1970","thousands of persons"),
     ((603,1023,648,1048),"893","Nursery","1970, White","October 1970","thousands of persons")])

add("S2-p001", "", (51,546,648,824),
    "About 35.5 million, or 20.0 percent, of the 177.4 million persons 1 year old and over who were living in the United States in March 1961 had moved at least once since March 1960. Although this overall mobility rate has reflected to some slight extent some of the postwar changes in business conditions, it has remained relatively stable in the 14 successive annual surveys conducted since 1948. The percentage of reported movers in the total population 1 year old and over has ranged from 18.6 to 21.0, with an average of 19.7, and has not shown any discernible trend.",
    [((171,545,224,574),"35.5","Moved at least once","Persons","March 1960 to March 1961","million persons"),
     ((357,545,410,574),"20.0","Moved at least once","Share","March 1960 to March 1961","percent"),
     ((584,545,647,574),"177.4","Population age 1 and over","Persons","March 1961","million persons"),
     ((236,574,253,600),"1","Population minimum age","Age","March 1961","years")],
    "No table: first four quantitative facts in the first body column, including age.")

add("S2-p002", "2", (39,794,651,1024),
    "Intracounty movers.--These are the persons who move within counties and who in recent surveys account for approximately 67 percent of all movers. Although a move from San Bernardino to Needles within San Ber- nardino County, California, could scarcely be regarded as a local change of residence which could be made without a change of job, a majority of local moves fall in the intracounty mover category. The category does, however, fail to include local changes of resi-",
    [((245,843,280,872),"67","Intracounty movers","Share of all movers","recent surveys described in 1961 report","percent"),
     ((120,1273,151,1298),"16","Interstate migrants","Share of all movers","recent surveys described in 1961 report","percent"),
     ((131,1559,165,1584),"15","Intrastate migrants","Share of all movers","recent surveys described in 1961 report","percent"),
     ((821,1215,874,1241),"22.1","Rural-nonfarm population","Overall mobility rate","1960-1961","percent")],
    "First body column has only three quantitative facts; fourth is the first rate in the second column (years and paragraph enumeration are not measurements). Text stops at a line boundary; retains printed hyphenation.")

add("S2-p004", "4", (49,278,657,533),
    'Mobility and marriage.--The late "teens" and the "twenties" are characterized by the exodus of children from the parental home--to the Armed Forces, to find employment outside the parental community, to college, but above all to get married. Among men 18 to 24 years old married and living with their wives, the mobility rate was 63.3 percent, whereas among single men of the same age, the mobility rate was only 19.6 percent. Among women in the same age group, the rate for wives living with their husbands was 55.2 percent.as compared',
    [((238,1568,283,1592),"15.9","14 to 17 years","Mobility rate, Male","March 1961","percent"),
     ((308,1568,352,1592),"17.5","14 to 17 years","Mobility rate, Female","March 1961","percent"),
     ((238,1588,283,1610),"19.6","18 and 19 years","Mobility rate, Male","March 1961","percent"),
     ((308,1588,352,1610),"34.9","18 and 19 years","Mobility rate, Female","March 1961","percent")])

add("S2-p005", "5", (59,859,673,1120),
    'Among the women 18 to 64 years old, the differences from expectation on the basis of "other never married" (single) women are of the same general character as those for men. The excess of actual movers over the number expected on the basis of the rates for single persons amounted to about 33 percent of all observed movers, the percentage was somewhat greater for intra- county movers, and 20 percent for migrants. For in- tracounty movers 18 to 24 years, the excess amounted to more than 50 percent of the total observed, and for',
    [((344,344,409,369),"46,388","Observed, Total 18 to 64 years","Total population","March 1961","thousands of persons"),
     ((441,344,498,369),"9,638","Observed, Total 18 to 64 years","Movers, Total","March 1961","thousands of persons"),
     ((350,370,409,393),"7,134","Observed, 18 to 24 years","Total population","March 1961","thousands of persons"),
     ((441,370,498,393),"2,357","Observed, 18 to 24 years","Movers, Total","March 1961","thousands of persons")])


add("S3-p005", "7", (103,442,665,661),
    "The total number of deaths returned for the registra- tion area of the United States for the year 1911 was 839,284. The estimated midyear population of this area was 59,275,977, or 63.1 per cent of the total popu- lation of the United States, and the death rate for the year was 14.2 per 1,000. This is the lowest death rate ever recorded for the registration area, as appears from the following statement:",
    [((345,770,381,794),"14.2","1911","Left series, Death rate","1911","deaths per 1,000 population"),
     ((627,770,662,794),"16.0","1903","Right series, Death rate","1903","deaths per 1,000 population"),
     ((345,785,381,807),"15.0","1910","Left series, Death rate","1910","deaths per 1,000 population"),
     ((627,785,662,807),"15.9","1902","Right series, Death rate","1902","deaths per 1,000 population")],
    "First table has two side-by-side year/rate series; year stubs are context, the two rate columns are targets. Text is a complete paragraph shorter than 80 words.")

add("S3-p006", "8", (127,630,684,954),
    "Of these 23 states, or 22 states if the partial regis- tration in North Carolina be disregarded, Kentucky and Missouri appear in the returns for the first time. The registration states formed less than one-half of the total number of states in the Union. Together with the District of Columbia, which is included in totals for the group of registration states but is else- where treated as a registration city, they comprised (including the North Carolina municipalities referred to) somewhat more than one-half of the total esti- mated midyear population in 1911 (54,385,234, or 57.9 per cent).",
    [((444,540,495,563),"1,000","North Carolina municipalities","Minimum population","1900","persons"),
     ((247,631,277,655),"23","Registration states","Including partial registration","1911","states"),
     ((382,631,411,655),"22","Registration states","Excluding partial registration","1911","states"),
     ((535,900,649,927),"54,385,234","Registration states and District of Columbia","Midyear population","1911","persons")],
    "No numeric data table; state/city lists are labels. First four measurements in the first column; dates and numbered footnotes are context, not measurement targets.")

add("S3-p008", "10", (149,675,704,940),
    "The states included in the registration area for the calendar year 1900 were Connecticut, Indiana, Maine, Massachusetts, Michigan, New Hampshire, New Jer- sey, New York, Rhode Island, and Vermont. The District of Columbia was also included. This group differs from the registration area of the Twelfth Cen- sus (year ending May 31, 1900) by the addition of Indiana. As constituted for the calendar year 1900 the group comprised a population of 19,960,742, or 26.3 per cent of the total for the United States in that year,",
    [((415,537,449,560),"14.9","Registration states (1900)","1911","1911","deaths per 1,000 population"),
     ((463,537,499,560),"15.6","Registration states (1900)","1910","1910","deaths per 1,000 population"),
     ((415,576,449,597),"15.4","Cities of 8,000 or more inhabitants in 1900","1911","1911","deaths per 1,000 population"),
     ((463,576,499,597),"16.2","Cities of 8,000 or more inhabitants in 1900","1910","1910","deaths per 1,000 population")])


add("S3-p010", "12", (719,808,1295,1108),
    "In comparing the rates of these foreign countries and cities it should be borne in mind that the figures, like the rates given for American states and cities, are crude rates only, uncorrected for differences in the composition of the population with respect to sex and age. The population of certain cities is favorably affected by large accessions of persons in early or middle life, which would tend to make the rates of such cities lower than those of cities depend- ent to a greater extent upon natural increase. The proportion of aged persons in the population has",
    [((289,366,321,387),"15.0","London","1911","1911","deaths per 1,000 persons living"),
     ((332,366,365,387),"13.7","London","1910","1910","deaths per 1,000 persons living"),
     ((289,380,321,401),"16.0","Edinburgh","1911","1911","deaths per 1,000 persons living"),
     ((332,380,365,401),"15.7","Edinburgh","1910","1910","deaths per 1,000 persons living")])

add("S3-p011", "13", (96,406,659,649),
    'A “specific death rate” may be technically defined as a death rate based upon a specified or limited group of population. As the age is the most important single factor affecting mortality, specific rates are primarily those of certain age groups. Sex should also be taken into consideration, and the most useful specific rates are those showing the relation of the deaths, by sex, of certain age groups to the correspond- ing population.',
    [((340,115,362,143),"5","Children","Age upper bound (under)","1911","years"),
     ((508,679,532,704),"11","Age groups","Number of groups","1911","groups"),
     ((377,759,397,785),"5","Children","Age upper bound (under)","1911","years"),
     ((428,785,459,811),"75","Persons","Age lower bound","1911","years")],
    "No table: first four measurements in the first column; page references and calendar dates excluded. Complete definition paragraph is shorter than 80 words.")

add("S3-p012", "14", (137,407,388,655),
    "REGISTRATION STATES California Colorado Connecticut Indiana Kentucky Maine Maryland Massachusetts Michigan Minnesota Missouri Montana New Hampshire New Jersey",
    [((402,407,440,430),"13.9","Registration states","Both sexes, All ages","1911","deaths per 1,000 population"),
     ((456,407,499,430),"112.9","Registration states","Both sexes, Under 1 year","1911","deaths per 1,000 population in age group"),
     ((402,434,440,456),"13.7","California","Both sexes, All ages","1911","deaths per 1,000 population"),
     ((456,434,499,456),"83.2","California","Both sexes, Under 1 year","1911","deaths per 1,000 population in age group")],
    "Table-only text region: contiguous row labels, shorter denominator. Decorative dot leaders and footnote symbols are structure, not row-label text; label-region scoring explicitly removes repeated dot leaders and footnote markers from both sides.")
RUNTIME[-1]["text_region"]["normalization"] = "table_labels_v1"


add("S4-p004", "7", (73,527,661,830),
    "Estimates of population for the years subsequent to the census are required for the annual reports of the Census Bureau and other Government bureaus. They are used in computing annual mortality rates of cities and states, for fixing the compensation of certain county officials, and in several states the census estimates of population are used as a basis for establishing the number of liquor licenses that may be granted. Many public-service corporations use our estimates as a basis for the expansion of their operations.",
    [((468,473,527,502),"8,000","Cities","Minimum population","April 15, 1910","persons"),
     ((1028,569,1097,599),"118.5","Intercensal interval","Elapsed time","1900-1910","months"),
     ((959,626,1025,654),"118.5","Annual increase calculation","Divisor","1900-1910","months"),
     ((812,653,846,681),"12","Annual increase calculation","Multiplier","1900-1910","months per year")],
    "No table and first column has only one measurement; continue to the first three measurements in the second column. Dates are period context, not numeric measurement targets.")

add("S4-p006", "9", (53,105,648,404),
    "In Table 3 (p. 15) is shown, by states and geographic divisions, the land area as of July 1, 1916, the popu- lation April 15, 1910, and June 1, 1900, and the esti- mated population July 1 of each year, 1910 to 1916, inclusive. Table 4 (p. 16) presents, by states and geographic divisions, the number of municipalities with 8,000 or more population April 15, 1910, with their popula- tion at that date and their estimated population July 1 of each year, 1910 to 1916, and the estimated population outside such municipalities.",
    [((548,572,566,594),"3","1,000,000 and over","Number in each group","July 1, 1916","municipalities"),
     ((628,572,644,594),"3","1,000,000 and over","Cumulative total","July 1, 1916","municipalities"),
     ((502,593,570,607),None,"900,000 to 1,000,000","Number in each group","July 1, 1916","municipalities"),
     ((628,590,644,609),"3","900,000 to 1,000,000","Cumulative total","July 1, 1916","municipalities")],
    "The second data row has a dot leader instead of a group count. Preserve that unavailable marker; do not infer zero from cumulative totals.")

add("S4-p010", "14", (86,466,290,688),
    "UNITED STATES Continental United States Outlying possessions Alaska Guam Hawaii Panama Canal Zone Philippine Islands Porto Rico Samoa Persons in military and naval service stationed abroad",
    [((297,473,363,491),None,"United States","Area, Total","1916","square miles"),
     ((370,473,430,491),None,"United States","Area, Land","1916","square miles"),
     ((297,496,363,519),"3,026,789","Continental United States","Area, Total","1916","square miles"),
     ((370,496,433,519),"2,973,890","Continental United States","Area, Land","1916","square miles")],
    "First data row has dot leaders in both area columns; do not substitute the continent's area or guess a total. Table-only passage uses contiguous row labels with shorter denominator.")
RUNTIME[-1]["text_region"]["normalization"] = "table_labels_v1"

add("S4-p011", "15", (77,375,368,598),
    "NEW ENGLAND DIVISION Maine New Hampshire Vermont Massachusetts Rhode Island Connecticut MIDDLE ATLANTIC DIVISION New York New Jersey Pennsylvania",
    [((369,332,448,357),"2,973,890","Continental United States","Land area","July 1, 1916","square miles"),
     ((465,332,549,357),"91,972,266","Continental United States","Census population","April 15, 1910","persons"),
     ((391,375,448,400),"61,976","New England division","Land area","July 1, 1916","square miles"),
     ((475,375,549,400),"6,552,681","New England division","Census population","April 15, 1910","persons")],
    "Table-only passage uses division headings and contiguous row labels; shorter denominator, table-label normalization.")
RUNTIME[-1]["text_region"]["normalization"] = "table_labels_v1"


def write():
    if (ROOT / "data/evaluation-freeze.json").exists():
        raise RuntimeError("Refusing to rewrite frozen annotations; use a versioned revision.")
    destination = ROOT / "data/annotations"
    destination.mkdir(parents=True, exist_ok=True)
    common = {"annotation_version": 1, "status": "visually_verified_configuration_freeze_pending",
              "coordinate_system": "normalized_top_left_ltrb",
              "author": "Codex visual transcription from rendered source images"}
    for name, pages in (("targets.json",RUNTIME),("references.json",REFERENCES)):
        (destination/name).write_text(json.dumps(dict(common,pages=pages),indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Wrote", len(RUNTIME), "pages; this serializer does not perform visual verification")


if __name__ == "__main__":
    write()
