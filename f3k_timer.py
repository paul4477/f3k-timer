import asyncio
import importlib
import pygame
import yaml
import logging

logging.basicConfig(format='%(asctime)s.%(msecs)03d %(name)s %(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S', level=logging.DEBUG, filename='f3k_timer.log')

logger = logging.getLogger(__name__)
pygame.mixer.init(frequency=44100, size=-16, channels=1)




"""try: 
    import plugin_pandora
except ImportError:
    logger.error("Could not import plugin_pandora (or maybe 'serial')")
try:
    import plugin_espnow
except ImportError:
    logger.error("Could not import plugin_espnow (or maybe the espnow library)")"""

from f3k_cl_event_engine import EventEngine, Clock


config_data = {}
main_config = {}



async def main():
    global config_data
    global main_config
    try:
        with open("config.yml", 'r') as config_file:
            
            config_data = list(yaml.load_all(config_file, Loader=yaml.SafeLoader))
    except Exception as e:
        logger.error(f"Error reading or parsing YAML config file: {e}")

    ## Create event manager    
    events = EventEngine()
    # player deals with updating event state
    import f3k_cl_player
    player = f3k_cl_player.Player(events)

    print(config_data)



    for config_section in config_data:
        #logger.info(f"Dealing with config section: {config_section}")
        if 'name' in config_section:
            #logger.info(f"Dealing with config section: {config_section}")
            if config_section['name'] == "main":
                global main_config
                main_config = config_section
                player.set_config(main_config)

            elif config_section['name'] == "web":
                web_config = config_section

            elif 'module' in config_section and 'object_name' in config_section:
                #logger.info(f"Dealing with config section: {config_section}")
                try:
                    module = importlib.import_module(config_section['module'])
                    plugin_object = getattr(module, config_section['object_name'])
                    logger.info(f"Successfully imported {config_section['object_name']} from {config_section['module']}")
                except (ImportError, AttributeError) as e:
                    logger.error(f"Could not import {config_section['object_name']} from '{config_section['module']}': {e}")
                    continue
                player.add_event_consumer(plugin_object(events, config_section))

        else:
            logger.error(f"Invalid configuration section: {config_section}")
            continue
    
    # web_server deals with messages to and from web interface
    import f3k_cl_web_server
    web_server = f3k_cl_web_server.WebFrontend(events, web_config)
    await web_server.startup()
    player.add_event_consumer(web_server)
    
    # AudioPlayer deals with audio playback at trigger points
    import f3k_cl_audio
    player.add_event_consumer(f3k_cl_audio.AudioPlayer(events, main_config))

    # Realtime Voice is used occaissionally to generate audio
    import f3k_cl_rtvoice
    player.add_event_consumer(f3k_cl_rtvoice.Voice(main_config.get('voice', 'en_US-lessac-medium'), events))

    ## External devices
    ## Serial interface to Pandora base station
    
    #player.add_event_consumer(plugin_pandora.Pandora(events))

    ## WiFi (ESPNow) broadcast interface to anything that is listening
    ## requires wlan device in appropriate state (see start.sh)
    
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
        
        # limit to x fps
        await clock.tick(24)
 
if __name__ == "__main__":
    pygame.init()
    asyncio.run(main())
    pygame.quit()
