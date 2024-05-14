from panda3d.core import BitMask32, TransformState
from panda3d.bullet import BulletRigidBodyNode, BulletPlaneShape, BulletBoxShape, BulletSphereShape, BulletCapsuleShape, XUp, YUp, ZUp, BulletTriangleMesh, BulletTriangleMeshShape, BulletDebugNode, BulletWorld
from ursina.vec3 import Vec3
from ursina.entity import Entity
from ursina import scene
from ursina.scripts.property_generator import generate_properties_for_class
import time

@generate_properties_for_class()
class PhysicsHandler(Entity):
    def __init__(self):
        self.world = BulletWorld()
        self.world.setGravity(Vec3(0, -9.806, 0))
        self._debug_node = BulletDebugNode('Debug')
        self._debug_node.showWireframe(True)
        self._debug_node.showConstraints(True)
        self._debug_node.showBoundingBoxes(False)
        self._debug_node.showNormals(False)
        self._debug_node_path = scene.attachNewNode(self._debug_node)
        self.world.setDebugNode(self._debug_node)
        super().__init__()

    def update(self):
        self.world.doPhysics(time.dt)

    def show_debug_setter(self, value):
        if value:
            self._debug_node_path.show()
        else:
            self._debug_node_path.hide()

physics_handler = PhysicsHandler()


class PlaneShape:
    def __init__(self, center=(0,0,0), normal=Vec3(0,1,0), offset=0):
        self.center = center
        self.normal = normal
        self.offset = offset

class BoxShape:
    def __init__(self, center=(0,0,0), size=(1,1,1)):
        self.center = center
        self.size = size

class SphereShape:
    def __init__(self, center=(0,0,0), radius=.5):
        self.center = center
        self.radius = radius

class CapsuleShape:
    def __init__(self, center=(0,0,0), radius=.5, height=2, axis='y'):
        self.center = center
        self.radius = radius
        self.height = height
        self.axis = axis

class MeshShape:
    def __init__(self, mesh=None, center=(0,0,0)):
        self.mesh = mesh
        self.center = center



class PhysicsBody:
    # copy the animation functionality from Entity
    animate = Entity.animate
    animate_position = Entity.animate_position
    animate_x = Entity.animate_x
    animate_y = Entity.animate_y
    animate_z = Entity.animate_z
    animate_rotation = Entity.animate_rotation
    animate_rotation_x = Entity.animate_rotation_x
    animate_rotation_y = Entity.animate_rotation_y
    animate_rotation_z = Entity.animate_rotation_z
    animate_scale = Entity.animate_scale
    animate_scale_x = Entity.animate_scale_x
    animate_scale_y = Entity.animate_scale_y
    animate_scale_z = Entity.animate_scale_z


    def __init__(self, name: str, world):
        self.world = world
        self.attached = False
        self._visible = False
        self.ignore_paused = False
        self.animations = []

    def __getattr__(self, attribute):
        return getattr(self.node_path.node(), attribute)


    def attach(self):
        if not self.attached:
            self.world.attachRigidBody(self.node_path.node())
            self.attached = True

    def detach(self):
        if self.attached:
            self.world.removeRigidBody(self.node_path.node())
            self.attached = False

    def remove(self):
        self.detach()
        self.node_path.removeNode()


    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, value: bool):
        self._visible = value
        if value:
            self.node_path.show()
        else:
            self.node_path.hide()

    @property
    def position(self):
        return Vec3(*self.node_path.getPos())

    @position.setter
    def position(self, value):
        self.node_path.setPos(Vec3(value))

    @property
    def x(self):
        return self.node_path.getX()

    @x.setter
    def x(self, value):
        self.node_path.setX(value)

    @property
    def y(self):
        return self.node_path.getY()

    @y.setter
    def y(self, value):
        self.node_path.setY(value)

    @property
    def z(self):
        return self.node_path.getZ()

    @z.setter
    def z(self, value):
        self.node_path.setZ(value)

    @property
    def rotation(self):
        rotation = self.node_path.getHpr()
        return Vec3(rotation[1], rotation[0], rotation[2])

    @rotation.setter
    def rotation(self, value):
        self.node_path.setHpr(Vec3(value[1], value[0], value[2]))

    @property
    def scale(self):
        scale = self.node_path.getScale()
        return Vec3(scale[0], scale[1], scale[2])

    @scale.setter
    def scale(self, value):
        value = [e if e!=0 else .001 for e in value]
        self.node_path.setScale(value[0], value[1], value[2])

    def add_force(self, force, point=(0,0,0)):
        if point != (0,0,0):
            self.node_path.node().applyForce(force, point)
        else:
            self.node_path.node().applyCentralForce(force)


class RigidBody(PhysicsBody):
    def __init__(self, shape, world=physics_handler.world, entity=None, mass=0, kinematic=False, friction=.5, mask=0x1):
        super().__init__(name='RigidBody', world=world)
        self.rigid_body_node = BulletRigidBodyNode('RigidBody')
        self.rigid_body_node.setMass(mass)
        self.rigid_body_node.setKinematic(kinematic)
        self.rigid_body_node.setFriction(friction)

        if entity:
            self.node_path = entity.getParent().attachNewNode(self.rigid_body_node)
            self.scale = entity.world_scale
            entity.reparentTo(self.node_path)
            self.position = entity.position
            entity.position = shape.center
            self.rotation = entity.rotation
            entity.world_scale = self.scale
        else:
            self.node_path = render.attachNewNode(self.rigid_body_node)
        self.node_path.node().setIntoCollideMask(BitMask32(mask))

        if not isinstance(shape, (list, tuple)):    # add just one shape
            self.node_path.node().addShape(_convert_shape(shape, entity, dynamic=not self.rigid_body_node.isStatic()))
        else:    # add multiple shapes
            for s in shape:
                self.node_path.node().addShape(_convert_shape(s, entity, dynamic=not self.rigid_body_node.isStatic()), TransformState.makePos(s.center))

        self.attach()
        self.node_path.setPythonTag('Entity', entity)


def _convert_shape(shape, entity, dynamic=True):
    if isinstance(shape, PlaneShape):
        return BulletPlaneShape(shape.normal, shape.offset)

    if isinstance(shape, BoxShape):
        return BulletBoxShape(Vec3(shape.size[0] / 2, shape.size[1] / 2, shape.size[2] / 2))

    if isinstance(shape, SphereShape):
        return BulletSphereShape(shape.radius)

    if isinstance(shape, CapsuleShape):
        if shape.axis == 'y':
            axis = YUp
        elif shape.axis == 'z':
            axis = ZUp
        elif shape.axis == 'x':
            axis = XUp
        return BulletCapsuleShape(shape.radius, shape.height-1, axis)

    if isinstance(shape, MeshShape) and entity:
        if shape.mesh is None and entity.model:
            mesh = entity.model
        else:
            mesh = shape.mesh

        geom_target = mesh.findAllMatches('**/+GeomNode').getPath(0).node().getGeom(0)
        output = BulletTriangleMesh()
        output.addGeom(geom_target)

        return BulletTriangleMeshShape(output, dynamic=dynamic)
    else:
        raise Exception("To use MeshShape you must specify at least one entity or mesh!")



if __name__ == '__main__':
    from ursina import Ursina, Entity, Vec3, time, EditorCamera, Sequence, Func, Wait, curve, Capsule

    app = Ursina(borderless=False)

    ground = Entity(model='plane', texture='grass', scale=30)
    RigidBody(shape=PlaneShape(), entity=ground)

    cube = Entity(model='cube', texture='white_cube', y=7)
    cube_body = RigidBody(shape=BoxShape(), entity=cube, mass=1)

    sphere = Entity(model='sphere', texture='brick', y=30)
    RigidBody(shape=SphereShape(), entity=sphere, mass=5)

    capsule = Entity(model=Capsule(height=2, radius=.5), texture='brick', y=17)
    RigidBody(shape=CapsuleShape(height=2, radius=.5), entity=capsule, mass=3)

    platform = Entity(model='cube', texture='white_cube', y=1, scale=(4,1,4))
    platform_rb = RigidBody(shape=BoxShape(), entity=platform, kinematic=True, friction=1)


    def input(key):
        if key == 'space up':
            e = Entity(model='cube', texture='white_cube', y=7)
            RigidBody(shape=BoxShape(), entity=e, mass=1, friction=1)
        elif key == 'up arrow':
            cube_body.add_force(force=Vec3(0, 1000, 0), point=Vec3(0,0,0))
            print('force applied')

    platform_move_sequence = Sequence(loop=True, entity=platform)
    state_duration = 2
    path = [Vec3(-2,1,-2), Vec3(2,1,-2), Vec3(0, 1, 2)]
    path.append(path[0])    # make it loop back to start

    for target_position in path:
        platform_move_sequence.append(Func(platform_rb.animate_position, target_position, duration=state_duration, curve=curve.linear))
        platform_move_sequence.append(Wait(state_duration))

    platform_move_sequence.generate()
    platform_move_sequence.start()

    physics_handler.show_debug = True


    EditorCamera()
    app.run()
