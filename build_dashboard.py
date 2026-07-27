#!/usr/bin/env python3
"""
Rebuild "The State of America's Health" dashboard from live CDC/SAMHSA/NCI sources.

Reads  template.html  (contains /*__DATA__*/ and /*__SEX__*/ placeholders)
Writes index.html     (self-contained, all data embedded)

Fully self-contained: run `python3 build_dashboard.py` anywhere the template is present
and there is outbound network access to data.cdc.gov. No local state required.

Data sources
------------
- State / age-adjustable chronic conditions : CDC BRFSS Prevalence (data.cdc.gov 'dttw-5yxu')
- Obesity by state (+ by sex)               : CDC DNPAO BRFSS      (data.cdc.gov 'hn4x-zwk7')
- Multi-year trends                          : same BRFSS dataset, US Overall, all years
- Real-time respiratory (weekly)             : NSSP ED visits % ('7xva-uux8') + ARI level ('f3zz-zga5')
- National overall / by-age / "different base" figures are curated constants from the most
  authoritative source per condition (NHANES/NHIS/SAMHSA/NCI); refreshed when CDC releases new years.
"""
import json, sys, time, datetime, urllib.request, urllib.parse

UA = {"User-Agent": "cdc-health-dashboard-builder/1.0"}
def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))

def soql(resource, params):
    return f"https://data.cdc.gov/resource/{resource}.json?" + \
        "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())

STATES = set("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT "
             "NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split())

# ---------- static / curated national figures (annual-cadence sources) ----------
OVERALL = [
  ("High blood pressure","Cardiometabolic",48,"119.9M","CDC · NHANES 2021–23","adults 18+ (measured)"),
  ("Prediabetes","Cardiometabolic",43,"115.2M","CDC","adults 18+ · ~8 in 10 undiagnosed"),
  ("Obesity","Cardiometabolic",40,"~106M","CDC · NHANES 2021–23","adults 18+ (measured) · severe ~10%"),
  ("Arthritis","Musculoskeletal",25,"~66M","CDC · BRFSS 2023","adults 18+ (diagnosed)"),
  ("Any mental illness","Mental & behavioral",23,"61.5M","SAMHSA · NSDUH 2024","adults 18+ · past year"),
  ("High cholesterol","Cardiometabolic",22,"—","CDC · NHIS","adults 18+ (ever told)"),
  ("Chronic pain","Musculoskeletal",21,"51.6M","CDC · 2021","adults 18+"),
  ("Depression","Mental & behavioral",20,"~53M","CDC · BRFSS 2023","adults 18+ (ever diagnosed)"),
  ("Anxiety disorder","Mental & behavioral",19,"~50M","CDC · 2024","adults 18+ (ever diagnosed)"),
  ("Substance use disorder","Mental & behavioral",17,"48.4M","SAMHSA · NSDUH 2024","age 12+ · past year"),
  ("Chronic kidney disease","Other / systemic",14,"~35.5M","CDC","adults 18+ · ~9 in 10 undiagnosed"),
  ("Diabetes","Cardiometabolic",12,"40.1M","CDC","adults 18+ (diagnosed + undiagnosed)"),
  ("Asthma (current)","Respiratory",10,"~26M","CDC · BRFSS 2023","adults 18+"),
  ("Heart disease","Cardiometabolic",7,"~17M","CDC · BRFSS 2023","adults 18+"),
  ("COPD","Respiratory",6,"~16M","CDC · BRFSS 2023","adults 18+"),
]
AGE = {"bands":["Younger","Middle age","Older"],"conditions":[
  {"name":"High blood pressure","src":"NHANES 2021–23","pts":[["18–39",23.4],["40–59",52.5],["60+",71.6]]},
  {"name":"Obesity","src":"NHANES 2021–23","pts":[["20–39",35.5],["40–59",46.4],["60+",38.9]]},
  {"name":"Diabetes (diagnosed)","src":"NHIS 2022 · approx.","pts":[["18–44",4],["45–64",12],["65+",20]]},
]}
TILEGRID = {"AK":[0,0],"ME":[0,11],"VT":[1,10],"NH":[1,11],"WA":[2,1],"ID":[2,2],"MT":[2,3],"ND":[2,4],
  "MN":[2,5],"WI":[2,6],"MI":[2,7],"NY":[2,9],"MA":[2,10],"OR":[3,1],"NV":[3,2],"WY":[3,3],"SD":[3,4],
  "IA":[3,5],"IL":[3,6],"IN":[3,7],"OH":[3,8],"PA":[3,9],"NJ":[3,10],"CT":[3,11],"CA":[4,1],"UT":[4,2],
  "CO":[4,3],"NE":[4,4],"MO":[4,5],"KY":[4,6],"WV":[4,7],"VA":[4,8],"MD":[4,9],"DE":[4,10],"RI":[4,11],
  "AZ":[5,2],"NM":[5,3],"KS":[5,4],"AR":[5,5],"TN":[5,6],"NC":[5,7],"SC":[5,8],"DC":[5,9],"OK":[6,4],
  "LA":[6,5],"MS":[6,6],"AL":[6,7],"GA":[6,8],"HI":[7,0],"TX":[7,4],"FL":[7,9]}

# BRFSS state measures: questionid -> (year, condId, label)
BRFSS_MEAS = {
  "DIABETE4": ("2024","DIABETES","Diabetes"),
  "_RFHYPE6": ("2023","HIBP","High blood pressure"),
  "ADDEPEV3": ("2024","DEPR","Depression"),
  "_CASTHM1": ("2024","ASTHMA","Current asthma"),
  "CHCCOPD3": ("2024","COPD","COPD"),
  "_DRDXAR2": ("2024","ARTH","Arthritis"),
  "CHCKDNY2": ("2024","CKD","Chronic kidney disease"),
  "_RFCHOL3": ("2023","HICHOL","High cholesterol"),
  "CHCOCNC1": ("2024","CANCER","Cancer (non-skin)"),
}
STATE_ORDER = ["OBESITY","HIBP","HICHOL","ARTH","DEPR","DIABETES","ASTHMA","CANCER","COPD","CKD"]

def latest_year(resource, qid):
    d = get(soql(resource, {"questionid": qid, "$select": "max(year)"}))
    return d[0].get("max_year") if d else None

def fetch_brfss_state():
    """Overall state values per condition, using the newest year actually available."""
    state = {}
    for qid,(yr,cid,label) in BRFSS_MEAS.items():
        ly = latest_year("dttw-5yxu", qid) or yr
        d = get(soql("dttw-5yxu", {"questionid":qid,"year":ly,"break_out":"Overall","response":"Yes",
                                   "$select":"locationabbr,data_value","$limit":"400"}))
        vals = {r["locationabbr"]:round(float(r["data_value"]),1) for r in d
                if r.get("data_value") and r["locationabbr"] in STATES}
        us = get(soql("dttw-5yxu", {"questionid":qid,"year":ly,"break_out":"Overall","response":"Yes",
                                    "locationabbr":"US","$select":"data_value"}))
        usv = round(float(us[0]["data_value"]),1) if us and us[0].get("data_value") else None
        state[cid] = {"label":label,"us":usv,"year":ly,"values":vals}
        print(f"  BRFSS {cid:9s} y{ly} states={len(vals)} US={usv}")
    return state

def fetch_brfss_sex():
    sex = {}
    for qid,(yr,cid,label) in BRFSS_MEAS.items():
        ly = latest_year("dttw-5yxu", qid) or yr
        sex[cid] = {}
        for s in ("Male","Female"):
            d = get(soql("dttw-5yxu", {"questionid":qid,"year":ly,"break_out":s,"response":"Yes",
                                       "$select":"locationabbr,data_value","$limit":"400"}))
            sex[cid][s] = {r["locationabbr"]:round(float(r["data_value"]),1) for r in d
                           if r.get("data_value") and r["locationabbr"] in STATES}
        print(f"  SEX   {cid:9s} M={len(sex[cid]['Male'])} F={len(sex[cid]['Female'])}")
    return sex

def fetch_obesity():
    """DNPAO obesity by state (Total) + by sex, newest year."""
    ly = get(soql("hn4x-zwk7", {"questionid":"Q036","$select":"max(yearstart)"}))[0].get("max_yearstart")
    def pull(strat_cat, strat):
        d = get(soql("hn4x-zwk7", {"yearstart":ly,"questionid":"Q036","stratificationcategory1":strat_cat,
                                   "stratification1":strat,"$select":"locationabbr,data_value","$limit":"200"}))
        return {r["locationabbr"]:round(float(r["data_value"]),1) for r in d
                if r.get("data_value") and r["locationabbr"] in STATES}
    total = pull("Total","Total")
    us = get(soql("hn4x-zwk7", {"yearstart":ly,"questionid":"Q036","locationabbr":"US",
                                "stratification1":"Total","$select":"data_value"}))
    usv = round(float(us[0]["data_value"]),1) if us and us[0].get("data_value") else None
    m = pull("Sex","Male"); f = pull("Sex","Female")
    print(f"  DNPAO OBESITY y{ly} states={len(total)} US={usv} M={len(m)} F={len(f)}")
    return ({"label":"Obesity","us":usv,"year":ly,"values":total}, {"Male":m,"Female":f})

TREND_MEAS = {"DIABETE4":"Diabetes","ADDEPEV3":"Depression","_CASTHM1":"Current asthma",
  "CHCCOPD3":"COPD","_DRDXAR2":"Arthritis","_RFHYPE6":"High blood pressure",
  "_RFCHOL3":"High cholesterol","CHCKDNY2":"Chronic kidney disease","CHCOCNC1":"Cancer (non-skin)"}
TREND_ID = {"DIABETE4":"DIABETES","ADDEPEV3":"DEPR","_CASTHM1":"ASTHMA","CHCCOPD3":"COPD",
  "_DRDXAR2":"ARTH","_RFHYPE6":"HIBP","_RFCHOL3":"HICHOL","CHCKDNY2":"CKD","CHCOCNC1":"CANCER"}
def fetch_trends():
    trend = {}
    for qid,label in TREND_MEAS.items():
        d = get(soql("dttw-5yxu", {"questionid":qid,"locationabbr":"US","break_out":"Overall","response":"Yes",
                                   "$select":"year,data_value","$order":"year","$limit":"60"}))
        series = {r["year"]:round(float(r["data_value"]),1) for r in d if r.get("data_value")}
        trend[TREND_ID[qid]] = {"label":label,"series":series}
    print(f"  TRENDS {len(trend)} conditions")
    return trend

def fetch_realtime():
    """Weekly respiratory: per-pathogen % ED visits (national, avg of M/F) + national ARI activity."""
    rt = {"cadence":"Updated weekly (Fridays) · auto-refreshed","items":[]}
    try:
        pmap = {"COVID-19":"COVID-19","Influenza":"Influenza","RSV":"RSV"}
        asof = None
        for disp, pat in pmap.items():
            rows = get(soql("7xva-uux8", {"geography":"United States","pathogen":pat,"demographics_type":"Sex",
                                          "$select":"week_end,demographics_values,percent_visits",
                                          "$order":"week_end DESC","$limit":"40"}))
            byweek = {}
            for r in rows:
                v = r.get("percent_visits")
                if r.get("demographics_values") in ("Male","Female") and v not in (None,""):
                    byweek.setdefault(r["week_end"], []).append(float(v))
            weeks = sorted(byweek)  # ascending
            if not weeks:
                continue
            def ov(w): return round(sum(byweek[w])/len(byweek[w]), 2)
            cur = ov(weeks[-1]); prev = ov(weeks[-5]) if len(weeks) >= 5 else ov(weeks[0])
            asof = max(asof, weeks[-1]) if asof else weeks[-1]
            delta = cur - prev
            arrow = "▲ rising" if delta > 0.05 else ("▼ falling" if delta < -0.05 else "→ flat")
            tone = "good" if cur < 1.5 else ("warn" if cur < 4 else "high")
            rt["items"].append({"name":disp,"level":f"{cur}% of ED visits","tone":tone,
                "note":f"{arrow} vs 4 weeks ago ({prev}%). Week ending {weeks[-1][:10]}."})
        # national ARI level distribution across states
        ari = get(soql("f3zz-zga5", {"$order":"week_end DESC","$limit":"400"}))
        wk = ari[0]["week_end"] if ari else None
        cur_ari = [r for r in ari if r.get("week_end")==wk]
        from collections import Counter
        cnt = Counter(r.get("label","?") for r in cur_ari if r.get("geography") in
                      {  # 50 states + DC by name
                        "Alabama","Alaska","Arizona","Arkansas","California","Colorado","Connecticut",
                        "Delaware","District of Columbia","Florida","Georgia","Hawaii","Idaho","Illinois",
                        "Indiana","Iowa","Kansas","Kentucky","Louisiana","Maine","Maryland","Massachusetts",
                        "Michigan","Minnesota","Mississippi","Missouri","Montana","Nebraska","Nevada",
                        "New Hampshire","New Jersey","New Mexico","New York","North Carolina","North Dakota",
                        "Ohio","Oklahoma","Oregon","Pennsylvania","Rhode Island","South Carolina","South Dakota",
                        "Tennessee","Texas","Utah","Vermont","Virginia","Washington","West Virginia","Wisconsin","Wyoming"})
        low = cnt.get("Very Low",0) + cnt.get("Low",0) + cnt.get("Minimal",0)
        total = sum(cnt.values()) or 1
        dominant = cnt.most_common(1)[0][0] if cnt else "Very Low"
        rt["overall"] = (f"Acute respiratory illness activity is {dominant} nationally — "
                         f"{low} of {total} states at Minimal/Low/Very Low this week.")
        rt["asof"] = (asof or wk or "")[:10]
        rt["asof"] = datetime.date.fromisoformat(rt["asof"]).strftime("%B %-d, %Y") if rt["asof"] else "recent week"
        print(f"  REALTIME asof {rt['asof']} pathogens={len(rt['items'])} ARI dominant={dominant}")
    except Exception as e:
        print(f"  REALTIME fetch failed ({e}); using placeholder")
        rt = {"asof":"unavailable","cadence":"Updated weekly (Fridays)",
              "overall":"Live respiratory data could not be retrieved this run — see CDC dashboards below.",
              "items":[{"name":"COVID-19","level":"—","tone":"good","note":"See CDC."},
                       {"name":"Influenza","level":"—","tone":"good","note":"See CDC."},
                       {"name":"RSV","level":"—","tone":"good","note":"See CDC."}]}
    return rt

def main():
    print("Fetching CDC data ...")
    state = fetch_brfss_state()
    sex = fetch_brfss_sex()
    ob_state, ob_sex = fetch_obesity()
    state["OBESITY"] = ob_state
    sex["OBESITY"] = ob_sex
    state_ordered = {k: state[k] for k in STATE_ORDER if k in state}
    trend = fetch_trends()
    realtime = fetch_realtime()

    DATA = {
      "meta": {"asof": datetime.date.today().strftime("%B %Y"),
               "pop": "~262 million U.S. adults (18+)",
               "built": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")},
      "overall": [dict(name=n,cat=c,pct=p,count=ct,src=s,base=b) for (n,c,p,ct,s,b) in OVERALL],
      "age": AGE,
      "trend": trend,
      "state": state_ordered,
      "tilegrid": TILEGRID,
      "realtime": realtime,
    }
    STATE_SEX = {k: sex[k] for k in STATE_ORDER if k in sex}

    tpl = open("template.html", encoding="utf-8").read()
    if "/*__DATA__*/" not in tpl or "/*__SEX__*/" not in tpl:
        print("ERROR: template.html missing placeholders", file=sys.stderr); sys.exit(1)
    html = tpl.replace("/*__DATA__*/", json.dumps(DATA, separators=(",",":"))) \
              .replace("/*__SEX__*/", json.dumps(STATE_SEX, separators=(",",":")))
    open("index.html","w",encoding="utf-8").write(html)
    print(f"\nWrote index.html ({len(html):,} bytes) · built {DATA['meta']['built']}")

if __name__ == "__main__":
    main()
