async def get_manga_data(manga_name: str, chapters: str, manga_channel: str):
    """Fetches manga details from Anilist API."""
    
    query = '''
    query ($search: String) {
      Media(type: MANGA, search: $search) {
        id
        title {
          romaji
          english
          native
        }
        status
        startDate { year month day }
        endDate { year month day }
        volumes
        chapters
        genres
        coverImage { large }
        siteUrl
      }
    }
    '''
    
    variables = {'search': manga_name}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(ANILIST_API_URL, json={'query': query, 'variables': variables}, timeout=10) as response:
                data = await response.json()
                
                if "data" in data and "Media" in data["data"]:
                    manga = data["data"]["Media"]
                    title = manga["title"]["english"] or manga["title"]["romaji"]
                    status = manga["status"].replace("FINISHED", "Completed").replace("RELEASING", "Ongoing")
                    start_date = f"{manga['startDate']['year']}-{manga['startDate']['month']}-{manga['startDate']['day']}"
                    end_date = f"{manga['endDate']['year']}-{manga['endDate']['month']}-{manga['endDate']['day']}" if manga['endDate']['year'] else "Ongoing"
                    volumes = manga["volumes"] or "N/A"
                    chapters = chapters if chapters else (manga["chapters"] or "N/A")
                    genres = ', '.join(manga["genres"])
                    manga_id = manga.get("id")

                    # Fetch Poster Image
                    poster_url = await get_poster(manga_id)

                    template = f"""
**{title}**
**──────────────────**
**➢ Type:** **Manga**
**➢ Status:** **{status}**
**➢ Start Date:** **{start_date}**
**➢ End Date:** **{end_date}**
**➢ Volumes:** **{volumes}**
**➢ Chapters:** **{chapters}**
**➢ Genres:** **{genres}**
**──────────────────**
**Manga Channel:** **{manga_channel}**
"""
                    return template, poster_url  
                else:
                    return "Manga not found. Please check the name and try again.", "https://envs.sh/YsH.jpg"
        
        except asyncio.TimeoutError:
            return "The request timed out. Please try again later.", "https://envs.sh/YsH.jpg"
