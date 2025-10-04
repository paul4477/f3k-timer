import asyncio
import pygame

import logging

logging.basicConfig(format='%(asctime)s.%(msecs)03d %(name)s %(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S', level=logging.WARN, filename='f3k_timer.log')

logger = logging.getLogger(__name__)
pygame.mixer.init(frequency=44100, size=-16, channels=1)
import f3k_cl_web_server
import f3k_cl_audio
import f3k_cl_player
import f3k_cl_rtvoice
try: 
    import plugin_pandora
except ImportError:
    logger.error("Could not import plugin_pandora (or maybe 'serial')")
try:
    import plugin_espnow
except ImportError:
    logger.error("Could not import plugin_espnow (or maybe the espnow library)")

from f3k_cl_event_engine import EventEngine, Clock


async def main():
    
    
    events = EventEngine()

    voice_name = 'en_US-lessac-medium'
    voice = f3k_cl_rtvoice.Voice(voice_name, events)

    web_server = f3k_cl_web_server.WebFrontend(events)
    await web_server.startup()
    
    player = f3k_cl_player.Player(events)

    player.add_event_consumer(f3k_cl_audio.AudioPlayer(events))
    #player.add_event_consumer(plugin_pandora.Pandora(events))
    #player.add_event_consumer(plugin_espnow.ESPNow(events))
    
    clock = Clock()
    TIMEREVENT = pygame.event.custom_type()
    pygame.time.set_timer(TIMEREVENT, 60000) 
    
    while player.is_running():
                       
        ## We could handle local keypress etc here
        ## If we wanted
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return
            elif ev.type == TIMEREVENT:
                fps = await clock.get_fps()
                logger.debug(f"fps: {fps:.1f}")

        
        await player.update()
        await web_server.update(player.state)
        # limit to x fps
        await clock.tick(24)
 
if __name__ == "__main__":
    pygame.init()
    asyncio.run(main())
    pygame.quit()
