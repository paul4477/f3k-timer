import asyncio
import pygame

import logging

logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S', level=logging.DEBUG, filename='f3k_timer.log')

logger = logging.getLogger(__name__)

import f3k_cl_web_server
import f3k_cl_audio
import f3k_cl_player
import plugin_pandora
import plugin_espnow

from f3k_cl_event_engine import EventEngine, Clock


async def main():
    
    events = EventEngine()

    web_server = f3k_cl_web_server.WebFrontend(events)
    await web_server.startup()
    

    audio_player = f3k_cl_audio.AudioPlayer(events)

    player = f3k_cl_player.Player(events)
    player.add_plugin(plugin_pandora.Pandora(events))
    #player.add_plugin(plugin_espnow.ESPNow(events))
    
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
