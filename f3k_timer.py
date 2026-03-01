import asyncio
import importlib
import pygame
import yaml
import logging

logging.basicConfig(format='%(asctime)s.%(msecs)03d %(name)s %(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S', level=logging.ERROR, filename='f3k_timer.log')

logger = logging.getLogger(__name__)
pygame.mixer.init(frequency=44100, size=-16, channels=1)

from f3k_cl_event_engine import EventEngine, Clock

async def main():
    config_data = {}
    main_config = {}
    try:
        with open("config.yml", 'r') as config_file:
            config_data = list(yaml.load_all(config_file, Loader=yaml.SafeLoader))
    except Exception as e:
        logger.error(f"Error reading or parsing YAML config file: {e}")

    ## Create event manager for passing events around    
    events = EventEngine()

    # player deals with updating event state
    import f3k_cl_player
    player = f3k_cl_player.Player(events)

    # Config for the main program and web server + plugins
    for config_section in config_data:
        if 'name' in config_section:
            ## Main config for prep time, use test time etc
            if config_section['name'] == "main":

                main_config = config_section
                player.set_config(main_config)

            ## Web server config - not likely to change from defaults
            elif config_section['name'] == "web":
                web_config = config_section

            ## Plugins - a section for each. We ignore sections that don't have module/object_name defined
            elif 'module' in config_section and 'object_name' in config_section:
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
    
    # Initialise audio library
    import audio_library
    audio_library.load_audio_library(main_config)

    # web_server deals with messages to and from web interface
    import f3k_cl_web_server
    web_server = f3k_cl_web_server.WebFrontend(events, web_config, player)
    await web_server.startup()
    player.add_event_consumer(web_server)
    
    # AudioPlayer deals with audio playback at trigger points
    import f3k_cl_audio
    player.add_event_consumer(f3k_cl_audio.AudioPlayer(events, main_config))

    # Realtime Voice is used occaissionally to generate audio
    import f3k_cl_rtvoice
    player.add_event_consumer(f3k_cl_rtvoice.Voice(main_config.get('voice', 'en_US-lessac-medium'), events))

    # Initialize player to not running state with "ShowTimeSection"
    player.init_pre_comp()
    
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
