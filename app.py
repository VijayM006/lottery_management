from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, session
import mysql.connector
import requests
from bs4 import BeautifulSoup
from collections import Counter
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import random
from datetime import date


app = Flask(__name__)



app.secret_key = "kerala_lottery"

# ─────────────────────────────────────────────
# DATABASE CONNECTION
# ─────────────────────────────────────────────

# DATABASE CONNECTION

def get_db():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Vijay@006",
        database="kerala_lottery"
    )
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lottery_results (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            lottery_name VARCHAR(100),
            draw_date   DATE,
            numbers     VARCHAR(255),
            source      VARCHAR(50),
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()


# ─────────────────────────────────────────────
# HOME
# ─────────────────────────────────────────────

@app.route("/")
def home():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) AS total FROM lottery_results")
    total = cursor.fetchone()["total"]
    cursor.execute("SELECT * FROM lottery_results ORDER BY draw_date DESC LIMIT 5")
    recent = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("home.html", total=total, recent=recent)


# ─────────────────────────────────────────────
# METHOD 1 — MANUAL ENTRY FORM
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# METHOD 2 — WEB SCRAPING (Kerala Lottery Site)
# ─────────────────────────────────────────────

def do_scrape():
    """
    Scrapes the latest Kerala Lottery results from keralalotteryresult.net
    and saves new entries to MySQL. Returns a status message.
    """
    url     = "https://www.keralalotteryresult.net/"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        return f"Request failed: {e}"

    soup    = BeautifulSoup(response.text, "html.parser")
    saved   = 0
    skipped = 0

    conn   = get_db()
    cursor = conn.cursor(dictionary=True)

    # Target result blocks — adjust selector if the site changes layout
    result_blocks = soup.find_all("div", class_="lottery-result")

    if not result_blocks:
        # Fallback: try to find any table with lottery data
        result_blocks = soup.find_all("table", class_="result-table")

    for block in result_blocks:
        try:
            # Extract lottery name
            name_tag = block.find("h2") or block.find("h3") or block.find("strong")
            lottery_name = name_tag.get_text(strip=True) if name_tag else "Unknown"

            # Extract draw date
            date_tag = block.find("span", class_="date") or block.find("td", class_="draw-date")
            raw_date = date_tag.get_text(strip=True) if date_tag else ""
            try:
                draw_date = datetime.strptime(raw_date, "%d-%m-%Y").strftime("%Y-%m-%d")
            except ValueError:
                draw_date = datetime.today().strftime("%Y-%m-%d")

            # Extract winning numbers
            num_tags = block.find_all("span", class_="number")
            if not num_tags:
                num_tags = block.find_all("td", class_="win-number")

            numbers = ",".join(tag.get_text(strip=True) for tag in num_tags if tag.get_text(strip=True).isdigit())

            if not numbers:
                skipped += 1
                continue

            # Avoid duplicate entries
            cursor.execute(
                "SELECT id FROM lottery_results WHERE lottery_name=%s AND draw_date=%s",
                (lottery_name, draw_date)
            )
            if cursor.fetchone():
                skipped += 1
                continue

            cursor.execute(
                "INSERT INTO lottery_results (lottery_name, draw_date, numbers, source) VALUES (%s, %s, %s, %s)",
                (lottery_name, draw_date, numbers, "scrape")
            )
            saved += 1

        except Exception:
            skipped += 1
            continue

    conn.commit()
    cursor.close()
    conn.close()

    return f"Scraping done — {saved} saved, {skipped} skipped."


@app.route("/scrape")
def scrape():
    message = do_scrape()
    flash(message, "info")
    return redirect(url_for("results"))


# ─────────────────────────────────────────────
# METHOD 3 — API FETCH
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# METHOD 3 — FETCH FROM keralalotteryresult.net
# (Replaces RapidAPI — acts as external data source)
# ─────────────────────────────────────────────

@app.route("/fetch-api")
def fetch_api():
    """
    Fetches the latest Kerala Lottery result from keralalotteryresult.net
    Treats the site as an external data source (like an API).
    """
    url     = "https://www.keralalotteryresult.net/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        flash(f"Connection failed: {e}", "danger")
        return redirect(url_for("results"))

    soup  = BeautifulSoup(response.text, "html.parser")
    saved = 0

    conn   = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        # ── Grab the first/latest result block ──────────
        # The site shows today's result at the top
        result_section = soup.find("div", class_="result-wrap") \
                      or soup.find("div", id="result") \
                      or soup.find("article")

        if not result_section:
            flash("Could not find result section on the page. Site layout may have changed.", "warning")
            return redirect(url_for("results"))

        # ── Lottery Name ─────────────────────────────────
        name_tag     = result_section.find("h2") or result_section.find("h1")
        lottery_name = name_tag.get_text(strip=True) if name_tag else "Kerala Lottery"
        # Clean up name (remove extra text like "Result Today")
        lottery_name = lottery_name.replace("Result", "").replace("Today", "").strip()

        # ── Draw Date ────────────────────────────────────
        date_tag = result_section.find("span", class_="date") \
                or result_section.find("time") \
                or result_section.find("p", class_="date")

        raw_date = date_tag.get_text(strip=True) if date_tag else ""

        draw_date = None
        for fmt in ["%d-%m-%Y", "%d/%m/%Y", "%B %d, %Y", "%d %B %Y"]:
            try:
                draw_date = datetime.strptime(raw_date, fmt).strftime("%Y-%m-%d")
                break
            except ValueError:
                continue

        if not draw_date:
            draw_date = datetime.today().strftime("%Y-%m-%d")

        # ── Winning Numbers ──────────────────────────────
        # Method 1: Find all spans or tds with digit content
        num_candidates = result_section.find_all(
            lambda tag: tag.name in ["span", "td", "li", "strong"]
                        and tag.get_text(strip=True).isdigit()
                        and 1 <= int(tag.get_text(strip=True)) <= 99
        )

        numbers = ",".join(t.get_text(strip=True) for t in num_candidates[:8])

        # Method 2 fallback — look for a dedicated numbers div
        if not numbers:
            num_div = result_section.find("div", class_="numbers") \
                   or result_section.find("ul", class_="winning")
            if num_div:
                numbers = ",".join(
                    t.get_text(strip=True)
                    for t in num_div.find_all(True)
                    if t.get_text(strip=True).isdigit()
                )

        if not numbers:
            flash("Numbers not found on page. The site layout may have changed.", "warning")
            return redirect(url_for("results"))

        # ── Duplicate check ───────────────────────────────
        cursor.execute(
            "SELECT id FROM lottery_results WHERE lottery_name=%s AND draw_date=%s",
            (lottery_name, draw_date)
        )
        if cursor.fetchone():
            flash(f"Result for {lottery_name} on {draw_date} already exists.", "warning")
        else:
            cursor.execute(
                "INSERT INTO lottery_results (lottery_name, draw_date, numbers, source) VALUES (%s, %s, %s, %s)",
                (lottery_name, draw_date, numbers, "api")
            )
            conn.commit()
            saved += 1
            flash(f"✅ Fetched & saved: {lottery_name} — {draw_date} | Numbers: {numbers}", "success")

    except Exception as e:
        flash(f"Parsing error: {e}", "danger")

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("results"))

# ─────────────────────────────────────────────
# ALL RESULTS PAGE
# ─────────────────────────────────────────────

@app.route("/results")
def results():
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM lottery_results ORDER BY draw_date DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("results.html", rows=rows)


# ─────────────────────────────────────────────
# DELETE A RESULT
# ─────────────────────────────────────────────

@app.route("/delete/<int:result_id>")
def delete_result(result_id):
    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM lottery_results WHERE id = %s", (result_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Result deleted.", "warning")
    return redirect(url_for("results"))


# ─────────────────────────────────────────────
# ANALYSIS — HOT / COLD / FREQUENCY
# ─────────────────────────────────────────────

def get_all_numbers():
    """Fetch all numbers from DB and return as a flat list of integers."""
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT numbers FROM lottery_results")
    rows   = cursor.fetchall()
    cursor.close()
    conn.close()

    all_numbers = []
    for row in rows:
        for n in row["numbers"].split(","):
            n = n.strip()
            if n.isdigit():
                all_numbers.append(int(n))
    return all_numbers


@app.route("/analysis")
def analysis():
    all_numbers = get_all_numbers()

    if not all_numbers:
        flash("No data available for analysis. Please add lottery results first.", "warning")
        return redirect(url_for("home"))

    frequency   = Counter(all_numbers)
    sorted_freq = sorted(frequency.items(), key=lambda x: x[1], reverse=True)

    hot_numbers  = sorted_freq[:10]   # Top 10 most drawn
    cold_numbers = sorted_freq[-10:]  # Top 10 least drawn

    return render_template(
        "analysis.html",
        frequency=sorted_freq,
        hot_numbers=hot_numbers,
        cold_numbers=cold_numbers,
        total_draws=len(all_numbers)
    )


# ─────────────────────────────────────────────
# PREDICTION — SUGGEST NUMBERS
# ─────────────────────────────────────────────

@app.route("/predict")
def predict():
    all_numbers = get_all_numbers()

    if not all_numbers:
        flash("No data available for prediction. Please add lottery results first.", "warning")
        return redirect(url_for("home"))

    frequency = Counter(all_numbers)

    # Strategy 1: Top 6 most frequent (Hot Pick)
    hot_pick = [n for n, _ in frequency.most_common(6)]

    # Strategy 2: Mix of hot (4) + cold (2) numbers
    sorted_freq   = sorted(frequency.items(), key=lambda x: x[1], reverse=True)
    hot_4         = [n for n, _ in sorted_freq[:4]]
    cold_2        = [n for n, _ in sorted_freq[-2:]]
    mixed_pick    = hot_4 + cold_2

    # Strategy 3: Weighted random — higher frequency = higher chance of being picked
    numbers_pool  = list(frequency.keys())
    weights_pool  = list(frequency.values())
    weighted_pick = random.choices(numbers_pool, weights=weights_pool, k=6)
    weighted_pick = list(set(weighted_pick))  # Remove duplicates
    # Fill up to 6 if duplicates reduced the count
    while len(weighted_pick) < 6:
        extra = random.choices(numbers_pool, weights=weights_pool, k=1)[0]
        if extra not in weighted_pick:
            weighted_pick.append(extra)

    return render_template(
        "predict.html",
        hot_pick=sorted(hot_pick),
        mixed_pick=sorted(mixed_pick),
        weighted_pick=sorted(weighted_pick)
    )


# ─────────────────────────────────────────────
# API ENDPOINT — JSON (optional use in frontend)
# ─────────────────────────────────────────────

@app.route("/api/results")
def api_results():
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM lottery_results ORDER BY draw_date DESC LIMIT 50")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    for row in rows:
        if row.get("draw_date"):
            row["draw_date"]   = str(row["draw_date"])
        if row.get("created_at"):
            row["created_at"]  = str(row["created_at"])
    return jsonify(rows)


@app.route("/api/analysis")
def api_analysis():
    all_numbers = get_all_numbers()
    frequency   = Counter(all_numbers)
    return jsonify({
        "total_numbers": len(all_numbers),
        "frequency": dict(sorted(frequency.items(), key=lambda x: x[1], reverse=True))
    })


# ─────────────────────────────────────────────
# AUTO SCRAPE — APSCHEDULER (every 24 hours)
# ─────────────────────────────────────────────

scheduler = BackgroundScheduler()
scheduler.add_job(do_scrape, "interval", hours=24, id="auto_scrape")
scheduler.start()


# ─────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
