def render_screen_stationary(stdscr):
    # Clear and refresh the screen for a blank canvas

    map_vector = []
    with open('mediummap.txt', 'r') as inf:
        map_vector = [[ x for x in s.strip()] for s in inf.readlines()]
    map_size_x=max([len(x) for x in map_vector])
    map_size_y=len(map_vector)

    # This is the starting position for the map
    # (eventually where the player will spawn)
    #
    #start at center of map (for now)
    map_pos_x=(map_size_x // 2)
    map_pos_y=(map_size_y // 2)

    # get screen_size
    height, width = stdscr.getmaxyx() 
    screen_center_x = width//2
    screen_center_y = height//2
    cursor_x=screen_center_x
    cursor_y=screen_center_y

    #initialize input char
    k=0
    while k != ord('q'):
        # get screen_size
        screen_height, screen_width = stdscr.getmaxyx() 
        stdscr.clear()

        # calculate the visible portion of the map
        # NOTE: for speed purposes, it might be better to 
        #       store these values and render from the original
        #       full-size map, rather than creating a new vector
        #       during each update cycle.
        min_vis_x = max(0,(map_pos_x-(screen_width//2-1)))
        min_vis_x += min_vis_x % 2
        min_vis_y = max(0,map_pos_y-(screen_height//2))
        max_vis_x = min(map_size_x, map_pos_x+(screen_width//2-1))
        max_vis_x -= max_vis_x % 2
        visible_map =[x[min_vis_x:max_vis_x+1] for x in map_vector[min_vis_y:max_vis_y+1]]
    
        #
        # Calculate the screen positions of the minimum and maximum
        # visible positions on the map for rendering
        #
        pos_min_vis_x = (width//2) - ((max_vis_x - min_vis_x)//2)
        pos_min_vis_y = (height//2) - ((max_vis_y - min_vis_y)//2)
        pos_max_vis_x = (width//2) + ((max_vis_x - min_vis_x)//2)
        pos_max_vis_y = (height//2) + ((max_vis_y - min_vis_y)//2)

        if k == curses.KEY_DOWN:
            cursor_y = min(pos_max_vis_y,cursor_y+1)
        elif k == curses.KEY_UP:
            cursor_y = max(pos_min_vis_y, cursor_y-1)
        elif k == curses.KEY_RIGHT:
            # this crashes with some window sizes due to cursor 
            # going over edge of screen
            cursor_x = min(pos_max_vis_x, cursor_x+2)
        elif k == curses.KEY_LEFT:
            cursor_x = max(pos_min_vis_x, cursor_x-2)

        map_cursor_y=pos_min_vis_y
        map_cursor_x=pos_min_vis_x
        for i,x in enumerate(visible_map):
            try:
                stdscr.addstr(map_cursor_y, map_cursor_x, ''.join(x))
                map_cursor_y += 1
            except _curses.error as e:
                pass

        # print debug info
        stdscr.move(0, 0)
        stdscr.addstr('cursor: '+str(cursor_y)+' '+ str(cursor_x))
        stdscr.move(1,0)
        stdscr.addstr('screen: '+str(height)+' '+str(width))
        stdscr.move(2,0)
        stdscr.addstr('vismap: '+str(pos_max_vis_y)+' '+str(pos_max_vis_x))
        stdscr.move(3,0)
        stdscr.addstr('viscrd: '+str(max_vis_y)+' '+str(max_vis_x))



        # move the cursor if needed
        try:
            stdscr.move(cursor_y, cursor_x)
        except _curses.error as e:
            stdscr.move(0,0)

        stdscr.refresh()
        k = stdscr.getch()


#    while k != ord('q'): 
#        # Initialization
#        stdscr.clear()
#        height, width = stdscr.getmaxyx()
#
#        # Wait for next input
#        k = stdscr.getch()

    while True:
        continue
        