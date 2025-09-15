import pygame


def run_round(round):
   

  pygame.init()
  X=800
  Y=600

  screen = pygame.display.set_mode((X,Y), pygame.NOFRAME | pygame.RESIZABLE)
  pygame.display.set_caption(f"{round}")
  clock = pygame.time.Clock()

  TIMEREVENT = pygame.USEREVENT + 1
  pygame.time.set_timer(TIMEREVENT, 340)  # 1 second = 1000 milliseconds
  pygame.event.set_blocked(pygame.MOUSEMOTION)

  SOUND_END = pygame.USEREVENT + 2
  SOUND_QUEUE = pygame.USEREVENT + 3
  sound_queue = []

    

  white = (255, 255, 255)
  green = (0, 255, 0)
  blue = (0, 0, 128)
  black = (0, 0, 0)
  font = pygame.font.Font('assets/fonts/consola.ttf', 120)

  font_small = pygame.font.Font('assets/fonts/consola.ttf', 25)

  pygame.mixer.init(frequency=44100, size=-16,channels=1)

  pygame.mixer.music.load('assets/sounds/countdown.mp3')



  effect_0 = pygame.mixer.Sound('assets/sounds/en/0000.wav')
  effect_1 = pygame.mixer.Sound('assets/sounds/en/0001.wav')
  effect_2 = pygame.mixer.Sound('assets/sounds/en/0002.wav')
  effect_3 = pygame.mixer.Sound('assets/sounds/en/0003.wav')
  effect_4 = pygame.mixer.Sound('assets/sounds/en/0004.wav')
  effect_5 = pygame.mixer.Sound('assets/sounds/en/0005.wav')
  effect_6 = pygame.mixer.Sound('assets/sounds/en/0006.wav')
  effect_7 = pygame.mixer.Sound('assets/sounds/en/0007.wav')
  effect_8 = pygame.mixer.Sound('assets/sounds/en/0008.wav')
  effect_9 = pygame.mixer.Sound('assets/sounds/en/0009.wav')
  effect_10 = pygame.mixer.Sound('assets/sounds/en/0010.wav')
  effect_11 = pygame.mixer.Sound('assets/sounds/en/0011.wav')
  effect_12 = pygame.mixer.Sound('assets/sounds/en/0012.wav')
  effect_13 = pygame.mixer.Sound('assets/sounds/en/0013.wav')
  effect_14 = pygame.mixer.Sound('assets/sounds/en/0014.wav')

  effect_15 = pygame.mixer.Sound('assets/sounds/en/0015.wav')
  effect_16 = pygame.mixer.Sound('assets/sounds/en/0016.wav')
  effect_17 = pygame.mixer.Sound('assets/sounds/en/0017.wav')
  effect_18 = pygame.mixer.Sound('assets/sounds/en/0018.wav')
  effect_19 = pygame.mixer.Sound('assets/sounds/en/0019.wav')
  effect_20 = pygame.mixer.Sound('assets/sounds/en/0020.wav')
  effect_30 = pygame.mixer.Sound('assets/sounds/en/0030.wav')
  effect_45 = pygame.mixer.Sound('assets/sounds/en/0045.wav')
  effect_second = pygame.mixer.Sound('assets/sounds/en/second0.wav')
  effect_seconds = pygame.mixer.Sound('assets/sounds/en/second1.wav')
  effect_minute = pygame.mixer.Sound('assets/sounds/en/minute0.wav')
  effect_minutes = pygame.mixer.Sound('assets/sounds/en/minute1.wav')

  effect_horn = pygame.mixer.Sound('assets/sounds/chord.wav')

  time_sounds ={0: effect_0,
                1: effect_1,
                2: effect_2,
                3: effect_3,
                4: effect_4,
                5: effect_5,
                6: effect_6,
                7: effect_7,
                8: effect_8,
                9: effect_9,
                10: effect_10,
                11: effect_11,
                12: effect_12,
                13: effect_13,
                14: effect_14,
                15: effect_15,
                16: effect_16,
                17: effect_17,
                18: effect_18,
                19: effect_19,
                20: effect_20,
                30: effect_30,
                45: effect_45,
                }



  countdown_start = pygame.time.get_ticks()
  last_countdown = 0
  duration = round.windowTime
  

  def queue_sounds(s1, delay, s2):
    sound_queue.append(s1)
    pygame.time.set_timer(SOUND_QUEUE, delay, loops=1)
    sound_queue.append(s2)
    pygame.event.post(pygame.event.Event(SOUND_QUEUE))

  running = True
  while running:
      #pygame.time.delay(100)
      #screen.blit(t, (t_x,100))
      
      #text = font.render(f'T {countdown}', True, green, blue)    
      #screen.blit(text, textRect)
      #t_x += 3
      


      clock.tick(80) # constrain to 40fps
      
      for event in pygame.event.get():
          print (event)
          if event.type == pygame.QUIT:
              running = False
          elif event.type == pygame.KEYDOWN:
              if event.key == pygame.K_q:  # press Q to quit
                  pygame.event.post(pygame.event.Event(pygame.QUIT))
              elif event.key == pygame.K_UP:
                pass
              elif event.key == pygame.K_UP:
                pass
              elif event.key == pygame.K_LEFT:
                if (event.mod & pygame.KMOD_CTRL): ## KMOD_SHIFT ## KMOD_ALT
                    countdown_start -= 30000
                else:
                    countdown_start -= 5000
              elif event.key == pygame.K_RIGHT:
                if (event.mod & pygame.KMOD_CTRL): ## KMOD_SHIFT ## KMOD_ALT
                    countdown_start += 30000
                else:
                    countdown_start += 5000

          elif event.type == TIMEREVENT:
              print(f"fps: {clock.get_fps():.1f}")
              #print(sound_queue)
              #print(countdown%10)
              pass
          elif event.type == SOUND_QUEUE:
            print ("SOUND_QUEUE")
            try: channel = sound_queue.pop(0).play()
            except IndexError:
                print ("SOUND_QUEUE triggered but nothing in the queue!")
            #pygame.time.set_timer(SOUND_QUEUE, 300, loops=1)
            #if channel:
            #   channel.set_endevent(SOUND_END)

          #elif event.type == SOUND_END:
          #  print ("SOUND_END")
            # if len(sound_queue) > 0:
            #   print ("setting 50ms timer")
              #  pygame.time.set_timer(SOUND_QUEUE, 5, loops=1)
      countdown = duration - int((pygame.time.get_ticks() - countdown_start)/1000)
      if countdown >= 0: #elif True:#event.type == TIMEREVENT:
              countdown = duration - int((pygame.time.get_ticks() - countdown_start)/1000)
              #effect.play()
              if True:#countdown != last_countdown:
                pygame.display.set_caption(f'Countdown: {countdown}')
                text = font.render(f'{int(countdown/60):02d}:{countdown%60:02d}', True, white, black)    
                text2 = font_small.render(f'Ticks {pygame.time.get_ticks():08d}', True, white, black)    
                textRect = text.get_rect()
                textRect2 = text2.get_rect()
                textRect.center = (X // 2, Y // 2)
                textRect2.center = (X // 2, Y // 3)
                screen.blit(text, textRect)
                screen.blit(text2, textRect2)
                if countdown <= 0: 
                  sound_queue.append(effect_horn)
                  pygame.event.post(pygame.event.Event(SOUND_QUEUE))
                  running = False
                



              ## Play sounds
              if countdown != last_countdown:
                
                if countdown % 15 == 0 and countdown > 60:
                  match (countdown%60):
                      case 45:
                        queue_sounds(time_sounds[int(countdown/60)], 400, time_sounds[45])
                      case 30:
                        queue_sounds(time_sounds[int(countdown/60)], 430, time_sounds[30])
                      case 15:
                        queue_sounds(time_sounds[int(countdown/60)], 420, time_sounds[15])
                      case 0:
                        queue_sounds(time_sounds[int(countdown/60)], 380, effect_minutes)                 
                
                match countdown:
                      case 60:
                        queue_sounds(effect_1, 400, effect_minute)
                      case 45:
                        queue_sounds(effect_45, 400, effect_seconds)
                      case 30:
                        pygame.mixer.music.play(0)
                        queue_sounds(effect_30, 400, effect_seconds)
                      case 0: 
                        sound_queue.append(effect_0)
                        pygame.event.post(pygame.event.Event(SOUND_QUEUE))
                      case x if x < 0:
                        pass
                      case x if x <=20 : 
                        sound_queue.append(time_sounds[x])
                        pygame.event.post(pygame.event.Event(SOUND_QUEUE))

              last_countdown = countdown

      pygame.display.update()

  pygame.quit()
      
