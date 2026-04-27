from playwright.sync_api import sync_playwright


def scrape_jobnet(search_term: str, max_results: int = 50, region: str = "HovedstadenOgBornholm") -> list[dict]:
    jobs = []
    seen_ids = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Listen to all XHR responses containing FindJob/Search
        def handle_response(response):
            if "/bff/FindJob/Search" in response.url and response.status == 200:
                try:
                    data = response.json()
                    for job in data.get("jobAds", []):
                        job_id = job.get("jobAdId", "")
                        if job_id in seen_ids:
                            continue
                        seen_ids.add(job_id)
                        jobs.append(
                            {
                                "title": job.get("occupation", ""),
                                "company": job.get("hiringOrgName", ""),
                                "location": job.get("postalDistrictName", ""),
                                "url": job.get("jobAdUrl", "") or f"https://jobnet.dk/find-job/{job_id}",
                                # "url": job.get("jobAdUrl", "") or f"https://jobnet.dk/find-job/stilling/{job_id}",
                                "id": job_id,
                                "deadline": job.get("applicationDeadline", ""),
                                "posted": job.get("publicationDate", ""),
                                "description": job.get("description", ""),
                            }
                        )
                except Exception as e:
                    print("Parse error:", e)

        page.on("response", handle_response)

        # Go to initial page
        page.goto(f"https://jobnet.dk/find-job?searchString={search_term}&regions={region}")
        page.wait_for_timeout(3000)

        # Click "Indlæs flere job" until gone or max_results
        while True:
            if len(jobs) >= max_results:
                break
            try:
                load_more = page.locator("button:has-text('Indlæs flere job')")
                if not load_more.is_visible():
                    break
                load_more.click()
                # Wait a bit for XHRs to finish
                page.wait_for_timeout(5000)
            except:
                break

    return jobs[:max_results]


if __name__ == "__main__":
    jobs = scrape_jobnet(search_term="data science", max_results=1)
    print(jobs)
