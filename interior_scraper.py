import json
import os
import asyncio
import nest_asyncio
from playwright.async_api import async_playwright

nest_asyncio.apply()

async def main():
    url = "https://interiorai.com/interior-designs/modern-style-fitness-gym-interior-with-dumbbell-stand-and-squat-rack-and-bench-177516"
    batch_size = 5
    batch_start = 27  # Resume from here

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_timeout(4000)

        # Grab initial styles and rooms
        def safe_strip(x): return x.strip() if x else ""
        await page.wait_for_selector("select")
        selects = await page.query_selector_all("select")

        style_options = await selects[0].query_selector_all("option")
        styles = [safe_strip(await opt.get_attribute("value")) for opt in style_options if safe_strip(await opt.get_attribute("value"))]

        room_options = await selects[1].query_selector_all("option")
        rooms = [safe_strip(await opt.text_content()) for opt in room_options if safe_strip(await opt.text_content())]

        print(f"✅ Found {len(styles)} styles and {len(rooms)} rooms.")

        batch_index = 0

        for style_start in range(0, len(styles), batch_size):
            style_slice = styles[style_start : style_start + batch_size]

            for room_start in range(0, len(rooms), batch_size):
                room_slice = rooms[room_start : room_start + batch_size]

                if batch_index < batch_start:
                    print(f"⏩ Skipping batch {batch_index}")
                    batch_index += 1
                    continue

                print(f"\n🔹 Batch {batch_index}: Styles {style_start}-{style_start + len(style_slice)-1}, Rooms {room_start}-{room_start + len(room_slice)-1}")
                data = []

                for style in style_slice:
                    try:
                        await page.goto(url)
                        await page.wait_for_timeout(3000)

                        selects = await page.query_selector_all("select")
                        await selects[0].select_option(value=style)
                        await page.wait_for_timeout(3000)

                        for room in room_slice:
                            try:
                                selects = await page.query_selector_all("select")
                                await selects[1].select_option(label=room)
                                await page.wait_for_timeout(4000)

                                # Prompt
                                try:
                                    prompt_elem = await page.wait_for_selector("h1.fake-input-box", timeout=10000)
                                    prompt = await prompt_elem.text_content()
                                except:
                                    prompt = ""
                                    print(f"⚠️ Prompt not found for {style}-{room}")

                                # Image URLs
                                img_urls = []
                                images = await page.query_selector_all("img")
                                for img in images:
                                    src = await img.get_attribute("src")
                                    if src and "/cdn-cgi/" in src and "assets/pencil-arrow.png" not in src:
                                        if not src.startswith("http"):
                                            src = "https://interiorai.com" + src
                                        img_urls.append(src)

                                if not img_urls:
                                    print(f"⚠️ No valid images found for {style}-{room}")

                                for img_url in img_urls:
                                    entry = {
                                        "style": style,
                                        "room": room,
                                        "prompt": prompt,
                                        "image_url": img_url
                                    }
                                    data.append(entry)
                                    print(f"✅ Collected image: {img_url}")

                            except Exception as e:
                                print(f"❌ Error scraping {style}-{room}: {e}")

                    except Exception as e:
                        print(f"❌ Error selecting style {style}: {e}")

                # Save batch
                json_path = f"batch_{batch_index}.json"
                jsonl_path = f"batch_{batch_index}.jsonl"

                with open(json_path, "w") as f:
                    json.dump(data, f, indent=2)

                with open(jsonl_path, "w") as f:
                    for item in data:
                        f.write(json.dumps(item) + "\n")

                print(f"✅ Batch {batch_index} saved: {json_path} ({len(data)} items)")
                batch_index += 1

        await browser.close()

asyncio.run(main())
