
from io import StringIO

import os
from os import path
import sys
from pprint import pprint
import time
import re
import traceback

import bpy

try:
    import chess.pgn
except Exception as e:
    print('chess module missing (pip install python-chess?)')
    traceback.print_exc()
    sys.exit(1)


# square size in blender units
SQUARE_SIZE = 3.0

# center of gravity for the pieces
Z_MAP = {
    'king': 2.32912,
    'queen': 2.0401,
    'bishop': 1.7937,
    'knight': 1.,
    'rook': 1.46252,
    'pawn': 1.35288,
}


def chess_to_coordinates(row, col, z):
    x_map = {'a': 0., 'b': 1., 'c': 2., 'd': 3., 'e': 4., 'f': 5., 'g': 6., 'h': 7.}
    y_map = {'1': 0., '2': 1., '3': 2., '4': 3., '5': 4., '6': 5., '7': 6., '8': 7.}
    
    return (x_map[row] + 0.5) * SQUARE_SIZE, (y_map[col] + 0.5) * SQUARE_SIZE, z


def clean():
    for action in bpy.data.actions:
        if action.users == 0:
            bpy.data.actions.remove(action)
    for mesh in bpy.data.meshes:
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def instantiate_piece(piece_name, player, board_location, name=None):
    col, row = board_location
    src_obj = bpy.context.scene.objects['template_' + piece_name]

    new_obj = src_obj.copy()
    new_obj.data = src_obj.data.copy()
    new_obj.animation_data_clear()

    if name:
        new_obj.name = name
    else:
        new_obj.name = piece_name + '.' + player + '.' + col + row
    
    bpy.context.scene.objects.link(new_obj)
    
    new_obj.location = chess_to_coordinates(col, row, Z_MAP[piece_name])
    new_obj.keyframe_insert(data_path='location')
    
    # physics
    bpy.context.scene.rigidbody_world.group.objects.link(new_obj)

    return new_obj


def initial_setup():
    clean()
    
    bpy.context.scene.layers[0] = True

    
    # remove stuff
    bpy.ops.object.select_all(action='DESELECT')
    for obj in filter(lambda x: not x.name.startswith('template_'), bpy.data.objects):
        obj.select = True
    bpy.ops.object.delete()

    
    bpy.context.scene.frame_set(1)
    bpy.context.scene.frame_end = 3000
    

    #bpy.ops.rigidbody.world_add()
    
    
    board_map = {}
    # PAWNS
    piece_name = 'pawn'
    for idx1, col in enumerate("abcdefgh"):
        for idx2, row in enumerate("27"):
            board_location = (col, row)
            if int(row) < 4:
                player = 'white'
            else:
                player = 'black'
            new_obj = instantiate_piece(piece_name, player, board_location)
            board_map[col + row] = new_obj

    # ROOKS
    piece_name = 'rook'
    for idx1, col in enumerate("ah"):
        for idx2, row in enumerate("18"):
            if int(row) < 4:
                player = 'white'
            else:
                player = 'black'
            board_location = (col, row)
            new_obj = instantiate_piece(piece_name, player, board_location)
            board_map[col + row] = new_obj
    # KNIGHTS
    piece_name = 'knight'
    for idx1, col in enumerate("bg"):
        for idx2, row in enumerate("18"):
            if int(row) < 4:
                player = 'white'
            else:
                player = 'black'
            board_location = (col, row)
            new_obj = instantiate_piece(piece_name, player, board_location)
            board_map[col + row] = new_obj
    # BISHOPS
    piece_name = 'bishop'
    for idx1, col in enumerate("cf"):
        for idx2, row in enumerate("18"):
            if int(row) < 4:
                player = 'white'
            else:
                player = 'black'
            board_location = (col, row)
            new_obj = instantiate_piece(piece_name, player, board_location)
            board_map[col + row] = new_obj
    # QUEENS
    piece_name = 'queen'
    for idx1, col in enumerate("d"):
        for idx2, row in enumerate("18"):
            if int(row) < 4:
                player = 'white'
            else:
                player = 'black'
            board_location = (col, row)
            new_obj = instantiate_piece(piece_name, player, board_location)
            board_map[col + row] = new_obj
    # KINGS
    piece_name = 'king'
    for idx1, col in enumerate("e"):
        for idx2, row in enumerate("18"):
            if int(row) < 4:
                player = 'white'
            else:
                player = 'black'
            board_location = (col, row)
            new_obj = instantiate_piece(piece_name, player, board_location)
            board_map[col + row] = new_obj
    
    # BOARD  
    bpy.ops.mesh.primitive_plane_add(view_align=False, enter_editmode=False, location=(0, 0, 0), layers=(True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False))
    bpy.context.selected_objects[0].name = 'ground'
    
    bpy.context.object.scale[1] = 4 * SQUARE_SIZE
    bpy.context.object.scale[0] = 4 * SQUARE_SIZE
    bpy.context.object.location[0] = 4 * SQUARE_SIZE
    bpy.context.object.location[1] = 4 * SQUARE_SIZE

    bpy.context.scene.rigidbody_world.group.objects.link(bpy.data.objects['ground'])

    # TODO: create checker texture
    checker_mat = bpy.data.materials.get('checker')
    bpy.data.objects['ground'].data.materials.append(checker_mat)

    bpy.context.scene.frame_set(2)
    bpy.context.scene.frame_set(3)
    bpy.context.scene.frame_set(1)
    
    bpy.data.objects['ground'].rigid_body.kinematic = True
    for piece in board_map.values():
        piece.rigid_body.kinematic = True


    return board_map
    


def load_pgn(pgn_path):
    print("Loading PGN " + str(pgn_path))
    try:
        with open(pgn_path) as pgn_file:
            game = chess.pgn.read_game(pgn_file)
    except Exception as e:
        print("Load PGN failed")
        traceback.print_exc()
        sys.exit(1)
    
    
    return game
    

def play(board_map, game, frames_per_move, n_fragments):
    start_time = time.time()

    board = game.board()
    for move_number, move in enumerate(game.main_line()):
        from_square = move.uci()[0:2]
        to_square = move.uci()[2:4]
        
        is_capture = board.is_capture(move)
        is_castling = board.is_castling(move)
        is_kingside_castling = board.is_kingside_castling(move)
        is_queenside_castling = board.is_queenside_castling(move)
        is_en_passant = board.is_en_passant(move)
        promotion = move.promotion
    
        print('{}: {}, cap: {}, castl: {}, promot: {}'.format((move_number // 2) + 1, move, is_capture, is_castling, promotion))


        if is_castling:
            king = board_map[from_square]
            
            if to_square == 'g1':
                rook_from = 'h1'
                rook_dest = 'f1'
            elif to_square == 'c1':
                rook_from = 'a1'
                rook_dest = 'd1'
            elif to_square == 'g8':
                rook_from = 'h8'
                rook_dest = 'f8'
            elif to_square == 'c8':
                rook_from = 'a8'
                rook_dest = 'd8'
            rook = board_map[rook_from]
            
            # insert keyframes
            king.keyframe_insert(data_path='location')
            rook.keyframe_insert(data_path='location')
            
            bpy.context.scene.frame_set(bpy.context.scene.frame_current + frames_per_move)
            
            # move king
            king.location = chess_to_coordinates(to_square[0], to_square[1], king.location.z)
            king.keyframe_insert(data_path='location')
            
            # move rook
            rook.location = chess_to_coordinates(rook_dest[0], rook_dest[1], rook.location.z)
            rook.keyframe_insert(data_path='location')
            
            # update board
            board_map.pop(from_square)
            board_map.pop(rook_from)
            
            board_map[to_square] = king
            board_map[rook_dest] = rook
            
            
        elif is_capture:
            # keyframe for previous position
            board_map[from_square].keyframe_insert(data_path='location')
            board_map[to_square].keyframe_insert('rigid_body.kinematic')
            
            bpy.context.scene.frame_set(bpy.context.scene.frame_current + 1)
            board_map[to_square].rigid_body.kinematic = False
            board_map[to_square].keyframe_insert('rigid_body.kinematic')
            bpy.context.scene.frame_set(bpy.context.scene.frame_current + -1)
            
            bpy.ops.object.select_all(action='DESELECT')
            board_map[to_square].select = True
            bpy.ops.object.add_fracture_cell_objects(source_limit=n_fragments)
            
            for obj in filter(lambda x: x.name.startswith(board_map[to_square].name + '_cell'), bpy.data.objects):
                bpy.context.scene.rigidbody_world.group.objects.link(obj)

            this_frame = bpy.context.scene.frame_current
            bpy.context.scene.frame_set(1)
            bpy.context.scene.frame_set(2)
            bpy.context.scene.frame_set(this_frame)
            
            for obj in filter(lambda x: x.name.startswith(board_map[to_square].name + '_cell'), bpy.data.objects):
                obj.rigid_body.kinematic = True
                obj.keyframe_insert('rigid_body.kinematic')

            # disable old piece
            for obj in bpy.data.objects:
                obj.select = False
            board_map[to_square].select = True
            bpy.context.scene.frame_set(0)
            board_map[to_square].rigid_body.collision_groups[0] = True
            board_map[to_square].keyframe_insert('rigid_body.collision_groups')
            board_map[to_square].hide = False
            board_map[to_square].keyframe_insert('hide')
            board_map[to_square].hide_render = False
            board_map[to_square].keyframe_insert('hide_render')
            
            bpy.context.scene.frame_set(this_frame - 1)
            board_map[to_square].rigid_body.collision_groups[0] = False
            board_map[to_square].keyframe_insert('rigid_body.collision_groups')
            board_map[to_square].hide = True
            board_map[to_square].keyframe_insert('hide')
            board_map[to_square].hide_render = True
            board_map[to_square].keyframe_insert('hide_render')
            
            
            
            # enable rigid body for cells
            bpy.context.scene.frame_set(this_frame - 1)
            for obj in filter(lambda x: x.name.startswith(board_map[to_square].name + '_cell'), bpy.data.objects):
                obj.rigid_body.kinematic = True
                obj.keyframe_insert('rigid_body.kinematic')
                obj.rigid_body.collision_groups[0] = False
                obj.keyframe_insert('rigid_body.collision_groups')
                
            bpy.context.scene.frame_set(this_frame)
            for obj in filter(lambda x: x.name.startswith(board_map[to_square].name + '_cell'), bpy.data.objects):
                obj.rigid_body.kinematic = False
                obj.keyframe_insert('rigid_body.kinematic')
                obj.rigid_body.collision_groups[0] = True
                obj.keyframe_insert('rigid_body.collision_groups')
            
            bpy.context.scene.frame_set(0)
            for obj in filter(lambda x: x.name.startswith(board_map[to_square].name + '_cell'), bpy.data.objects):
                obj.hide = True
                obj.keyframe_insert('hide')
                obj.hide_render = True
                obj.keyframe_insert('hide_render')
            bpy.context.scene.frame_set(this_frame - 1)
            for obj in filter(lambda x: x.name.startswith(board_map[to_square].name + '_cell'), bpy.data.objects):
                obj.hide = False
                obj.keyframe_insert('hide')
                obj.hide_render = False
                obj.keyframe_insert('hide_render')
            
            
            
            # timestep
            bpy.context.scene.frame_set(this_frame + frames_per_move)
        
            # move piece
            board_map[from_square].location = chess_to_coordinates(to_square[0], to_square[1], board_map[from_square].location.z)
            board_map[from_square].keyframe_insert(data_path='location')
            
            
            
            
            # actually play the move
            board_map[to_square] = board_map[from_square]
            board_map.pop(from_square)

        else:
            # simple move
            # keyframe for previous position
            board_map[from_square].keyframe_insert(data_path='location')
            
            # timestep
            bpy.context.scene.frame_set(bpy.context.scene.frame_current + frames_per_move)
            
            # move piece
            board_map[from_square].location = chess_to_coordinates(to_square[0], to_square[1], board_map[from_square].location.z)
            board_map[from_square].keyframe_insert(data_path='location')
            
            # play the move on board
            board_map[to_square] = board_map[from_square]
            board_map.pop(from_square)

        if promotion:
            TURN_COLOR_MAP = { True: 'white', False: 'black' }
            player = TURN_COLOR_MAP[board.turn]

            promoted_piece = chess.PIECE_NAMES[promotion]
            print('Promoted to: ' + str(promoted_piece))

            (col, row) = (to_square[0], to_square[1])
            new_obj = instantiate_piece(promoted_piece, player, (col, row), name='{}.{}.promoted.{}{}'.format(promoted_piece, player, col, row))
            board_map[col + row] = new_obj
            
            # TODO
            # disable physics until now, enable after
            # distroy promoted pawn
            # update board_map
            print('TODO: promotion')
            break

        # update the board
        board.push(move)
        
        if 'CHESS_FRACTURE_TEST' in os.environ and move_number > 10:
            print('Early exit because CHESS_FRACTURE_TEST is defined')
            break
    # end for moves
    
    # assign materials
    white_mat = bpy.data.materials.get('white')
    black_mat = bpy.data.materials.get('black')
    
    whites_re = re.compile(r'.*white.*')
    blacks_re = re.compile(r'.*black.*')
    for obj in bpy.data.objects:
        if whites_re.match(obj.name):
            obj.data.materials.append(white_mat)
        elif blacks_re.match(obj.name):
            obj.data.materials.append(black_mat)

    # compute some stats
    end_time = time.time()
    duration = end_time - start_time
    print('Duration: ' + str(duration))
    # end def play



def main():
    if 'CHESS_FRACTURE_FRAMES_PER_MOVE' in os.environ:
        frames_per_move = int(os.environ['CHESS_FRACTURE_FRAMES_PER_MOVE'])
    else:
        frames_per_move = 20
    print("CHESS_FRACTURE_FRAMES_PER_MOVE=" + str(frames_per_move))

    if 'CHESS_FRACTURE_FRAGMENTS' in os.environ:
        n_fragments = int(os.environ['CHESS_FRACTURE_FRAGMENTS'])
    else:
        n_fragments = 10
    print("CHESS_FRACTURE_FRAGMENTS=" + str(n_fragments))

    if 'CHESS_FRACTURE_PGN_PATH' in os.environ:
        print('CHESS_FRACTURE_PGN_PATH=' + str(os.environ['CHESS_FRACTURE_PGN_PATH']))
        game = load_pgn(os.environ['CHESS_FRACTURE_PGN_PATH'])
    else:
        game = load_pgn('/work/input.pgn')


    variant = game.board().uci_variant
    if variant != 'chess':
        sys.stdout.write('Unsupported game type {}\n'.format(variant))
        sys.exit(1)

    board_map = initial_setup()
    print('Board setup done')

    try:
        play(board_map, game, frames_per_move, n_fragments)
        print('Simulation done')
    except Exception as e:
        print('Simulation failed')
        traceback.print_exc()
        sys.exit(1)

    try:
        if 'CHESS_FRACTURE_OUT_BLEND' in os.environ:
            save_file = os.environ['CHESS_FRACTURE_OUT_BLEND']
        
            bpy.ops.wm.save_as_mainfile(filepath=save_file)
        
            print('File saved as "{}"'.format(save_file))
        
            sys.exit(0)  # happy path
    except Exception as e:
        print('Save failed ' + str(e))
        traceback.print_exc()
        sys.exit(1)
    # end def main


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('main failed :' + str(e))
        traceback.print_exc()
        sys.exit(1)
