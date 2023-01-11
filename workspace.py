import pdb
import sys,os
import curses, _curses
import json
from collections import defaultdict

import locale
locale.setlocale(locale.LC_ALL,'')
code = locale.getpreferredencoding()


class Resource:
    def __init__(self,resource_id,name):
        self.m_id=resource_id
        self.m_name=name


class EntityResource(Resource):
    """ A Resource object that posesses entity data -- that is --
        information about how to be rendered to the screen, whether
        other screen items collide with it, etc. 
    """
    def __init__(self,resource_id,name, **kwargs):
        super().__init__(resource_id,name)
        self.m_sprite=kwargs['sprite']
        self.m_collision=kwargs['collision']
        self.m_destructible=kwargs['destructible']

class ItemResource(EntityResource):
    def __init__(self,resource_id,name, **kwargs):
        super().__init__(resource_id,name,**kwargs['entity'])
        self.item_class = kwargs['item_class']
        # 3x3 sprite is represented as a list of strings in the json file
        # This helps to display the sprite in a legible fashion, since json
        # does not allow for multi-line strings.  Also makes rendering to the
        # screen easy with a for loop over the list.
        self.m_sprite_3x3 = kwargs['sprite_3x3']

class StructureResource(EntityResource):
    def __init__(self,resource_id,name, **kwargs):
        super().__init__(resource_id,name,**kwargs['entity'])



# collection of all game resources including entity metadata (inc: descriptions & ascii art)
# eventually will include NPC-character data, structures (though these are also entities)
class ResourcePack:
    def __init__(self, resources_file='resources.json'):
        self.m_item_resources={}
        self.m_structure_resources={}
        self.m_ids={}
        # read in resource metadata from the file resources.json. Higher-level resources
        # like ItemResource are composed of a base Resource, an EntityResource (which
        # describes rendering and game-map functions), and some additional metadata.
        with open(resources_file,'r') as inf:
            resources=json.load(inf)
            for item in resources['item_data']:
                kwargs=item['item']
                kwargs['entity']=item['entity']
                ir = ItemResource(item['id'],item['name'],**kwargs)
                self.m_item_resources[item['id']]=ir
                self.m_ids[item['id']]=ir
            for structure in resources['structure_data']:
                kwargs=structure['structure']
                kwargs['entity']=structure['entity']
                sr = StructureResource(structure['id'],structure['name'],**kwargs)
                self.m_structure_resources[structure['id']]=sr            
                self.m_ids[structure['id']]=sr


class GameObject:
    m_resources=ResourcePack()
    def __init__(self):
        return


class Game(GameObject):
    def __init__(self):
        self.m_player=self.initialize_player()
        self.m_map=self.initialize_map()

    def initialize_player(self):
        return Player(self)

    def initialize_map(self):
        return GameMap('smallmap.txt','smallmap.json')

class Entity(GameObject):
    def __init__(self,resource_id,y_pos,x_pos,resource,game_map):
        self.m_id=resource_id
        self.m_y=y_pos
        self.m_x=x_pos
        self.m_resource=resource
        self.m_map=game_map

    def destroy(self):
        self.m_map.destroy_entity(self)


class GameMap(GameObject):
    class missingdict(defaultdict):
        def __missing__(self,key):
            return self.default_factory()

    def __init__(self,map_file,metadata_file):
        # read the map file into a list of list of chars
        # map height and width are stored for slightly faster computation
        #
        # NOTE: maps are defined as rectangular; a map with uneven line-lengths
        #       will result in undefined behavior
        with open(map_file, 'r') as inf:
            self.m_map = [[ x for x in s.strip()] for s in inf.readlines()]
            self.m_height = len(self.m_map)
            self.m_width = len(self.m_map[0])
        
        # read the metadata file into the relevant member variables.
        # metadata file currently includes the following:
        #   - list of entities
        #   - player start position
        # will eventually include color data, connections
        # to other maps (ladders, exits, &c.) 
        with open(metadata_file, 'r') as inf:
            metadata=json.load(inf)

            # entities are stored in a modified class based on collections.defaultdict(list),
            # wherein the __missing__ method is changed to return the default value without
            # automatically generating an entry under that key in the dict.  This allows
            # the user to perform lookups without first checking for the presence of a key,
            # while also not incurring the penalty of an ever-ballooning dict size.
            # NOTE: add the first item to the list using + [...] syntax, not .append(...) syntax
            self.m_entities=GameMap.missingdict(list)
            for e in metadata['item_entities']:
                self.m_entities[(e['y_pos'],e['x_pos'])]+=[Entity(e['resource_id'],e['y_pos'],e['x_pos'],
                    self.m_resources.m_ids[e['resource_id']],self)]
            self.m_py=metadata['player_start_y']
            self.m_px=metadata['player_start_x']
            self.m_player_facing=metadata['player_facing']

    def get_p_yx(self):
        return (self.m_py,self.m_px)

    # editable function for character movement
    # will allow for collision detection etc.
    def move(self,ch):
        old_y,old_x=self.m_py,self.m_px
        if ch == curses.KEY_DOWN:
            self.m_player_facing="down"
            new_y,new_x=self.m_py+1,self.m_px
            if not any([x.m_resource.m_collision for x in self.m_entities[(new_y,new_x)]]):
                self.m_py = min(self.m_height-1,new_y)
        elif ch == curses.KEY_UP:
            self.m_player_facing="up"            
            new_y,new_x=self.m_py-1,self.m_px
            if not any([x.m_resource.m_collision for x in self.m_entities[(new_y,new_x)]]):
                self.m_py = max(0, new_y)
        elif ch == curses.KEY_RIGHT:
            self.m_player_facing="right"            
            new_y,new_x=self.m_py,self.m_px+2
            if not any([x.m_resource.m_collision for x in self.m_entities[(new_y,new_x)]])\
            and not any([x.m_resource.m_collision for x in self.m_entities[(new_y,new_x-1)]]):
                self.m_px = min(self.m_width, new_x)
                self.m_px -= self.m_px % 2 # in case map is odd-width
        elif ch == curses.KEY_LEFT:
            self.m_player_facing="left"            
            new_y,new_x=self.m_py,self.m_px-2
            if not any([x.m_resource.m_collision for x in self.m_entities[(new_y,new_x)]])\
            and not any([x.m_resource.m_collision for x in self.m_entities[(new_y,new_x+1)]]):
                self.m_px = max(0, new_x)
                self.m_px += self.m_px % 2 # in case map is odd-width

        # report if the player didn't move
        return(int((old_y,old_x)!=(self.m_py,self.m_px)))

    def get_top_entity(self,y,x):
        return self.m_entities[y,x][-1] if self.m_entities[y,x] else None

    def spawn_item(self, y, x, item):
        self.m_entities[(y,x)]+=[(Entity(item.m_id,y,x,item.m_resource,self))]

    def destroy_entity(self,e):
        self.m_entities[e.m_y,e.m_x].remove(e)


class Player(GameObject):
    def __init__(self,game):
        self._inv_maxsize = 5
        self._sel_inv_slot = 0
        self.m_inventory = [None] * self._inv_maxsize
        self.m_game=game

    def take_action(self,k):
        my_map=self.m_game.m_map
        # move the player if UP,DOWN,RIGHT, or LEFT are pressed
        if k in [curses.KEY_DOWN,curses.KEY_UP,curses.KEY_RIGHT,curses.KEY_LEFT]:
            my_map.move(k)
        if k in range(ord('0'),ord('9')):
            self.set_inv_slot(k-49)
        if k == ord(' '):
            p_y,p_x=my_map.get_p_yx()
            self.pick_up(my_map.get_top_entity(p_y,p_x))
        if k == ord('d'):
            self.drop(self.get_inv_slot())


    def pick_up(self,entity):
        if entity is not None:
            try:
                inv_slot=self.m_inventory.index(None)
                self.m_inventory[inv_slot]=Item(entity.m_id)
                # create item from entity's resource ID
                entity.destroy()
            except:
                # TODO there's probably a more elegant solution
                # if there's no empty inv. slot, do nothing
                pass

    def set_inv_slot(self,new_val):
        if new_val in range(self._inv_maxsize):
            self._sel_inv_slot=new_val
        return(int(new_val in range(self._inv_maxsize)))

    def get_inv_slot(self):
        return self._sel_inv_slot

    def drop(self,inv_slot):
        # inv_slot is an int in range(_inv_maxsize)
        if inv_slot in range(self._inv_maxsize) and self.m_inventory[inv_slot] is not None:
            item=self.m_inventory[inv_slot]
            py,px=self.m_game.m_map.get_p_yx()
            self.m_game.m_map.spawn_item(py,px,item)
            self.m_inventory[inv_slot]=None


class Item(GameObject):
    def __init__(self,resource_id):
        self.m_id=resource_id
        self.m_resource=self.m_resources.m_ids[resource_id]

 
class GameWindow():
    def __init__(self,stdscr,my_game):
        self.m_game=my_game
        self.stdscr=stdscr
        self.m_hud_win=HUDWindow(stdscr,my_game)
        self.m_map_win=MapWindow(stdscr,my_game)

    def render(self):
        self.stdscr.erase()

        self.m_map_win.update_size()
        self.m_hud_win.update_size()

        self.m_map_win.render()
        self.m_hud_win.render()


class Window():
    def __init__(self,parent_scr,height,width,starty=0,startx=0):
        self.screen_height, self.screen_width = parent_scr.getmaxyx() 
        self.height=height
        self.width=width
        self.m_win=parent_scr.subwin(self.height,self.width,starty,startx)
        self.parent_scr=parent_scr
        return

    def update_size(self):
        self.screen_height, self.screen_width = self.parent_scr.getmaxyx()


class MapWindow(Window):
    def __init__(self,parent_scr,my_game):
        self.m_game=my_game
        self.m_map=my_game.m_map
        h,w = parent_scr.getmaxyx() 
        super().__init__(parent_scr,h,w,0,0)
        return

    def render(self):
        # recalculate screen size values 
        # (these can change if the user resizes the screen)
        screen_center_y = self.height // 2
        screen_center_x = self.width // 2

        # screen-map offset:
        # NOTE: true value, can be negative. If using this val to render to screen,
        #       be sure to check that you're writing in-bounds.
        map_offset_y = screen_center_y - self.m_map.m_py
        map_offset_x = screen_center_x - self.m_map.m_px
        # visible portion of map
        min_vis_y = max(0,-1*map_offset_y)
        max_vis_y = min(self.m_map.m_height,(self.height-1)-map_offset_y)
        min_vis_x = max(0,-1*map_offset_x) 
        max_vis_x = min(self.m_map.m_width,(self.width-1)-map_offset_x)

        # render the map to the screen
        map_cursor_y,map_cursor_x = max(0,map_offset_y),max(0,map_offset_x)
        for i,l in enumerate(self.m_map.m_map):
            # skip ahead until you get into the visible section
            if i < min_vis_y:
                continue
            # stop iterating when you get past the vis. section
            if i > max_vis_y:
                break

            # NOTE: try catch is to ignore out of bounds error. This error is thrown if, while 
            #       the program is running, the terminal is resized such that a character is
            #       written in the the bottom right-hand corner of the screen.  The cursor 
            #       attempts to advance to a position outside of the screen boundary => exception
            #
            #       passing does not break the program because bounds-checking in this render function
            #       ensures that the cursor will not write out of bounds.
            try:
                self.m_win.addstr(map_cursor_y,map_cursor_x,str(''.join(l[min_vis_x:max_vis_x+1])))
            except _curses.error as e:
                pass
            map_cursor_y += 1
    
        # render all in-bounds entities associated with the map.
        for y,x in self.m_map.m_entities:
            pos_y=y+map_offset_y
            pos_x=x+map_offset_x
            # using map_offset numbers, check if the coords
            # are in bounds before accessing object 
            if pos_y>=0 and pos_y<self.height and pos_x>=0 and pos_x<self.width:
                for e in self.m_map.m_entities[(y,x)]:
                    try:
                        self.m_win.addch(pos_y, pos_x, e.m_resource.m_sprite)
                    except _curses.error as e:
                        pass

        # player's position relative to the screen
        player_screen_y=screen_center_y
        player_screen_x=screen_center_x

        # render the player to the screen
        # TODO: this should be replaced with a more elegant solution in the future
        #       I would prefer to use a dict to look up multiple sprites for entities
        try:
            player_sprite="@"
            player_attr = 0
            player_attr ^= curses.A_BOLD
            player_attr ^= curses.color_pair(1)
            self.m_win.addch(player_screen_y,player_screen_x,player_sprite,player_attr)
        except _curses.error as e:
            pass
    
        self.m_win.addstr(0,0,str(self.m_map.m_py)+' '+str(self.m_map.m_px))

    def update_size(self):
        super().update_size()
        self.height=self.screen_height
        self.width=self.screen_width


class HUDWindow(Window):
    def __init__(self,parent_scr,my_game):
        self.m_game=my_game
        self.m_player=my_game.m_player
        parent_h,parent_w = parent_scr.getmaxyx() 
        h,w = 7, parent_w-1
        super().__init__(parent_scr,h,w,parent_h-h,1)
        return

    def render(self):
        self.m_win.erase()
        for j,item in enumerate(self.m_player.m_inventory):
            inv_slot=self.m_win.derwin(self.height-2,7,1,(7*j)+1)
            inv_slot.box()
            if item is not None:
                attr=0
                # if we're about to render the selected inventory item
                # the nwe do a bit of special stuff
                if j==self.m_player.get_inv_slot():
                    # make the sprite bold
                    attr ^= curses.A_BOLD
                    # show the name of the selected item
                    self.m_win.addstr(0,2,item.m_resource.m_name.capitalize())

                for k,l in enumerate(item.m_resource.m_sprite_3x3):
                    inv_slot.addstr(k+1,2,l,attr) 

    def update_size(self):
        super().update_size()
        # TODO:
        # you can use this area to update the HUD size 
        # if the window changes size
        #

def repl(stdscr):
    curses.start_color()
    curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_BLACK)

    my_game=Game()
    game_screen=GameWindow(stdscr,my_game)

    my_map=my_game.m_map
    my_player=my_game.m_player

    #initialize input char
    k=0
    while k != ord('q'):
        my_player.take_action(k)
        game_screen.render()
        k = stdscr.getch()


def main():
    curses.wrapper(repl)


if __name__ == '__main__':
    main()
