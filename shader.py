# vim:ts=4:et
# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

import sys, traceback
from struct import unpack
from pprint import pprint

import bpy
from bpy.types import Operator, Menu
from bl_operators.presets import AddPresetBase
from bpy.props import BoolProperty, FloatProperty, StringProperty, EnumProperty
from bpy.props import BoolVectorProperty, CollectionProperty, PointerProperty
from bpy.props import FloatVectorProperty, IntProperty
from mathutils import Vector,Matrix,Quaternion

from .mu import MuEnum, MuMaterial
from . import shaderprops
from .colorprops import  MuMaterialColorPropertySet
from .float2props import MuMaterialFloat2PropertySet
from .float3props import MuMaterialFloat3PropertySet
from .textureprops import MuMaterialTexturePropertySet
from .vectorprops import MuMaterialVectorPropertySet

main_block = (
    ("node", "UV Map", 'ShaderNodeUVMap', (-920, -80)),
    ("setval", "UV Map", "label", ""),
    ("node", "BaseShader", 'ShaderNodeBsdfPrincipled', (-100, 280)),
    ("setval", "BaseShader", "label", ""),
    ("node", "EmissiveShader", 'ShaderNodeEmission', (-100, -280)),
    ("setval", "EmissiveShader", "label", ""),
    ("setval", "EmissiveShader", "inputs[0].default_value", (0,0,0,1)),
    ("node", "Reroute0", 'NodeReroute', (180, -320)),
    ("setval", "Reroute0", "label", ""),
    ("node", "Reroute1", 'NodeReroute', (180, 220)),
    ("setval", "Reroute1", "label", ""),
    ("node", "Add Shader", 'ShaderNodeAddShader', (200, 260)),
    ("setval", "Add Shader", "label", ""),
    ("setval", "Add Shader", "hide", True),
    ("node", "Material Output", 'ShaderNodeOutputMaterial', (320, 260)),
    ("setval", "Material Output", "label", ""),
    ("setval", "Material Output", "hide", True),
    ("link", "BaseShader", "BSDF", "Add Shader", "inputs[0]"),
    ("link", "Add Shader", "Shader", "Material Output", "Surface"),
    ("link", "EmissiveShader", "Emission", "Reroute0", "Input"),
    ("link", "Reroute0", "Output", "Reroute1", "Input"),
    ("link", "Reroute1", "Output", "Add Shader", "inputs[1]"),
)

transparency_block = (
    ("link", "_MainTex:invertAlpha", "Value", "BaseShader", "Transmission"),
    ("matset", "blend_method", 'ADD'), #FIXME should be alpha blend, but...
)

opaque_block = (
    ("matset", "blend_method", 'OPAQUE'),
)

specularity_block = (
    ("link", "_MainTex:invertAlpha", "Value", "BaseShader", "Roughness"),
)

mainTex_block = (
    ("node", "_MainTex:frame", 'NodeFrame', (-820, 200)),
    ("setval", "_MainTex:frame", "label", "_MainTex"),
    ("setval", "_MainTex:frame", "hide", True),
    ("node", "_MainTex:texture", 'ShaderNodeTexImage', (-480, 140)),
    ("setval", "_MainTex:texture", "label", "Texture"),
    ("setval", "_MainTex:texture", "hide", True),
    ("setparent", "_MainTex:texture", "_MainTex:frame"),
    ("node", "_MainTex:mapping", 'ShaderNodeMapping', (-600, 140)),
    ("setval", "_MainTex:mapping", "label", "Mapping"),
    ("setval", "_MainTex:mapping", "hide", True),
    ("setval", "_MainTex:mapping", "vector_type", 'POINT'),
    ("setparent", "_MainTex:mapping", "_MainTex:frame"),
    ("node", "_Color", 'ShaderNodeRGB', (-480, 80)),
    ("setval", "_Color", "label", "_Color"),
    ("setval", "_Color", "hide", True),
    ("setval", "_Color", "outputs[0].default_value", (1,1,1,1)),
    ("setparent", "_Color", "_MainTex:frame"),
    ("node", "_MainTex:invertAlpha", 'ShaderNodeMath', (-360, 80)),
    ("setval", "_MainTex:invertAlpha", "label", "Invert Alpha"),
    ("setval", "_MainTex:invertAlpha", "hide", True),
    ("setval", "_MainTex:invertAlpha", "operation", 'SUBTRACT'),
    ("setparent", "_MainTex:invertAlpha", "_MainTex:frame"),
    ("node", "_MainTex:multiply", 'ShaderNodeMixRGB', (-360, 140)),
    ("setval", "_MainTex:multiply", "label", ""),
    ("setval", "_MainTex:multiply", "hide", True),
    ("setval", "_MainTex:multiply", "blend_type", 'MULTIPLY'),
    ("setval", "_MainTex:multiply", "inputs[0].default_value", 1),
    ("setparent", "_MainTex:multiply", "_MainTex:frame"),
    ("link", "UV Map", "UV", "_MainTex:mapping", "Vector"),
    ("link", "_MainTex:mapping", "Vector", "_MainTex:texture", "Vector"),
    ("link", "_MainTex:texture", "Color", "_MainTex:multiply", "Color1"),
    ("link", "_Color", "Color", "_MainTex:multiply", "Color2"),
    ("link", "_MainTex:texture", "Alpha", "_MainTex:invertAlpha", "inputs[1]"),
    ("link", "_MainTex:multiply", "Color", "BaseShader", "Base Color"),
    ("settex", "_MainTex:texture", "image", "_MainTex", "tex"),
    ("settex", "_MainTex:mapping", "translation.xy", "_MainTex", "offset"),
    ("settex", "_MainTex:mapping", "scale.xy", "_MainTex", "scale"),
    ("set", "_Color", "outputs[0].default_value",
            "color.properties", "_Color"),
)

bumpmap_block = (
    ("node", "_BumpMap:frame", 'NodeFrame', (-800, -40)),
    ("setval", "_BumpMap:frame", "label", "_BumpMap"),
    ("node", "_BumpMap:mapping", 'ShaderNodeMapping', (-600, -80)),
    ("setval", "_BumpMap:mapping", "label", "Mapping"),
    ("setval", "_BumpMap:mapping", "hide", True),
    ("setval", "_BumpMap:mapping", "vector_type", 'POINT'),
    ("setparent", "_BumpMap:mapping", "_BumpMap:frame"),
    ("node", "_BumpMap:texture", 'ShaderNodeTexImage', (-480, -80)),
    ("setval", "_BumpMap:texture", "label", "Normal Map"),
    ("setval", "_BumpMap:texture", "hide", True),
    ("setval", "_BumpMap:texture", "color_space", 'NONE'),
    ("setparent", "_BumpMap:texture", "_BumpMap:frame"),
    ("node", "_BumpMap:normal", 'ShaderNodeNormalMap', (-360, -80)),
    ("setval", "_BumpMap:normal", "label", ""),
    ("setval", "_BumpMap:normal", "hide", True),
    ("setparent", "_BumpMap:normal", "_BumpMap:frame"),
    ("link", "UV Map", "UV", "_BumpMap:mapping", "Vector"),
    ("link", "_BumpMap:mapping", "Vector", "_BumpMap:texture", "Vector"),
    ("link", "_BumpMap:texture", "Color", "_BumpMap:normal", "Color"),
    ("link", "_BumpMap:normal", "Normal", "BaseShader", "Normal"),
    ("settex", "_BumpMap:texture", "image", "_BumpMap", "tex"),
    ("settex", "_BumpMap:mapping", "translation.xy", "_BumpMap", "offset"),
    ("settex", "_BumpMap:mapping", "scale.xy", "_BumpMap", "scale"),
)

emissive_block = (
    ("node", "_Emissive:frame", 'NodeFrame', (-800, -180)),
    ("setval", "_Emissive:frame", "label", "_Emissive"),
    ("node", "_EmissiveColor", 'ShaderNodeRGB', (-480, -300)),
    ("setval", "_EmissiveColor", "label", "_EmissiveColor"),
    ("setval", "_EmissiveColor", "hide", True),
    ("setparent", "_EmissiveColor", "_Emissive:frame"),
    ("node", "_Emissive:mapping", 'ShaderNodeMapping', (-600, -240)),
    ("setval", "_Emissive:mapping", "label", "Mapping"),
    ("setval", "_Emissive:mapping", "hide", True),
    ("setval", "_Emissive:mapping", "vector_type", 'POINT'),
    ("setparent", "_Emissive:mapping", "_Emissive:frame"),
    ("node", "_Emissive:texture", 'ShaderNodeTexImage', (-480, -240)),
    ("setval", "_Emissive:texture", "label", "EmissiveShader Map"),
    ("setval", "_Emissive:texture", "hide", True),
    ("setparent", "_Emissive:texture", "_Emissive:frame"),
    ("node", "_Emissive:multiply", 'ShaderNodeMixRGB', (-360, -240)),
    ("setval", "_Emissive:multiply", "label", "Multiply"),
    ("setval", "_Emissive:multiply", "hide", True),
    ("setval", "_Emissive:multiply", "blend_type", 'MULTIPLY'),
    ("setval", "_Emissive:multiply", "inputs[0].default_value", 1),
    ("setparent", "_Emissive:multiply", "_Emissive:frame"),
    ("link", "_Emissive:mapping", "Vector", "_Emissive:texture", "Vector"),
    ("link", "_EmissiveColor", "Color", "_Emissive:multiply", "Color2"),
    ("link", "_Emissive:texture", "Color", "_Emissive:multiply", "Color1"),
    ("link", "UV Map", "UV", "_Emissive:mapping", "Vector"),
    ("link", "_Emissive:multiply", "Color", "EmissiveShader", "Color"),
    ("settex", "_Emissive:texture", "image", "_Emissive", "tex"),
    ("settex", "_Emissive:mapping", "translation.xy", "_Emissive", "offset"),
    ("settex", "_Emissive:mapping", "scale.xy", "_Emissive", "scale"),
    ("set", "_EmissiveColor", "outputs[0].default_value",
            "color.properties", "_EmissiveColor"),
)

ksp_specular = main_block + mainTex_block + specularity_block + opaque_block
ksp_bumped = main_block + mainTex_block + bumpmap_block + opaque_block
ksp_bumped_specular = main_block + mainTex_block + specularity_block + bumpmap_block + opaque_block
ksp_emissive_diffuse = main_block + mainTex_block + emissive_block + opaque_block
ksp_emissive_specular = (main_block + mainTex_block + emissive_block
                         + specularity_block + opaque_block)
ksp_emissive_bumped_specular = (main_block + mainTex_block + emissive_block
                                + specularity_block + bumpmap_block
                                + opaque_block)
ksp_alpha_cutoff = ()
ksp_alpha_cutoff_bumped = ()
ksp_alpha_translucent = ()
ksp_alpha_translucent_specular = main_block + mainTex_block + specularity_block + transparency_block
ksp_unlit_transparent = ()
ksp_unlit = ()
ksp_diffuse = main_block + mainTex_block + opaque_block
ksp_particles_alpha_blended = main_block + mainTex_block + transparency_block
ksp_particles_additive = main_block + mainTex_block

ksp_shaders = {
"KSP/Specular":ksp_specular,
"KSP/Bumped":ksp_bumped,
"KSP/Bumped Specular":ksp_bumped_specular,
"KSP/Emissive/Diffuse":ksp_emissive_diffuse,
"KSP/Emissive/Specular":ksp_emissive_specular,
"KSP/Emissive/Bumped Specular":ksp_emissive_bumped_specular,
"KSP/Alpha/Cutoff":ksp_alpha_cutoff,
"KSP/Alpha/Cutoff Bumped":ksp_alpha_cutoff_bumped,
"KSP/Alpha/Translucent":ksp_alpha_translucent,
"KSP/Alpha/Translucent Specular":ksp_alpha_translucent_specular,
"KSP/Alpha/Unlit Transparent":ksp_unlit_transparent,
"KSP/Unlit":ksp_unlit,
"KSP/Diffuse":ksp_diffuse,
"KSP/Particles/Alpha Blended":ksp_particles_alpha_blended,
"KSP/Particles/Additive":ksp_particles_additive,
}

def node_node(name, nodes, s):
    n = nodes.new(s[2])
    #print(s[2])
    #for i in n.inputs:
    #    print(i.name)
    #for o in n.outputs:
    #    print(o.name)
    n.name = "%s.%s" % (name, s[1])
    n.label = s[1]
    n.location = s[3]
    if s[2] == "ShaderNodeMaterial":
        n.material = bpy.data.materials.new(n.name)

def node_link(name, nodes, links, s):
    n1 = nodes["%s.%s" % (name, s[1])]
    n2 = nodes["%s.%s" % (name, s[3])]
    if s[2][:7] == "outputs":
        op = eval("n1.%s" % s[2])
    else:
        op = n1.outputs[s[2]]
    if s[4][:6] == "inputs":
        ip = eval("n2.%s" % s[4])
    else:
        ip = n2.inputs[s[4]]
    links.new(op, ip)

def node_set(name, matprops, nodes, s):
    n = nodes["%s.%s" % (name, s[1])]
    str="'%s' in matprops.%s" % (s[4], s[3])
    if eval(str, {}, locals()):
        str="n.%s = matprops.%s['%s'].value" % (s[2], s[3], s[4])
        exec(str, {}, locals())

def mat_set(mat, s):
    setattr(mat, s[1], s[2])

def node_settex(name, matprops, nodes, s):
    n = nodes["%s.%s" % (name, s[1])]
    tex = matprops.texture.properties[s[3]]
    img = tex.tex
    if img[-4:-3] == ".":
        img = img[:-4]
    #FIXME doesn't work
    #offset = tex.offset / tex.scale
    #offset = Vector((tex.offset.x/tex.scale.x, tex.offset.y / tex.scale.y))
    offset = tex.offset
    scale = tex.scale
    #print("img =", img)
    if img in bpy.data.images:
        tex = bpy.data.images[img]
        exec("n.%s = %s" % (s[2], s[4]), {}, locals())

def node_setval(name, nodes, s):
    n = nodes["%s.%s" % (name, s[1])]
    #print(s)
    exec("n.%s = %s" % (s[2], repr(s[3])), {}, locals())

def node_setparent(name, nodes, s):
    n = nodes["%s.%s" % (name, s[1])]
    p = "%s.%s" % (name, s[2])
    #print("n.parent = nodes['%s']" % (p,))
    exec("n.parent = nodes['%s']" % (p,), {}, locals())

def node_call(name, nodes, s):
    n = nodes["%s.%s" % (name, s[1])]
    exec("n.%s" % s[2], {}, locals())

def create_nodes(mat):
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    while len(links):
        links.remove(links[0])
    while len(nodes):
        nodes.remove(nodes[0])
    if mat.mumatprop.shaderName not in ksp_shaders:
        print("Unknown shader: '%s'" % mat.mumatprop.shaderName)
        return
    shader = ksp_shaders[mat.mumatprop.shaderName]
    print(mat.mumatprop.shaderName)
    for s in shader:
        #print(s)
        try :
            if s[0] == "node":
                node_node(mat.name, nodes, s)
            elif s[0] == "link":
                node_link(mat.name, nodes, links, s)
            elif s[0] == "set":
                node_set(mat.name, mat.mumatprop, nodes, s)
            elif s[0] == "matset":
                mat_set(mat, s)
            elif s[0] == "settex":
                node_settex(mat.name, mat.mumatprop, nodes, s)
            elif s[0] == "setval":
                node_setval(mat.name, nodes, s)
            elif s[0] == "setparent":
                node_setparent(mat.name, nodes, s)
            elif s[0] == "call":
                node_call(mat.name, nodes, s)
            else:
                print("unknown shader command", s[0])
        except:
           print("Exception in node setup code:")
           traceback.print_exc(file=sys.stdout)

def set_tex(mu, dst, src):
    try:
        tex = mu.textures[src.index]
        dst.tex = tex.name
        dst.type = tex.type
    except IndexError:
        pass
    dst.scale = src.scale
    dst.offset = src.offset

def make_shader_prop(muprop, blendprop):
    for k in muprop:
        item = blendprop.add()
        item.name = k
        item.value = muprop[k]

def make_shader_tex_prop(mu, muprop, blendprop):
    for k in muprop:
        item = blendprop.add()
        item.name = k
        set_tex(mu, item, muprop[k])

def make_shader4(mumat, mu):
    mat = bpy.data.materials.new(mumat.name)
    matprops = mat.mumatprop
    matprops.shaderName = mumat.shaderName
    make_shader_prop(mumat.colorProperties, matprops.color.properties)
    make_shader_prop(mumat.vectorProperties, matprops.vector.properties)
    make_shader_prop(mumat.floatProperties2, matprops.float2.properties)
    make_shader_prop(mumat.floatProperties3, matprops.float3.properties)
    make_shader_tex_prop(mu, mumat.textureProperties, matprops.texture.properties)
    create_nodes(mat)
    return mat

def make_shader(mumat, mu):
    return make_shader4(mumat, mu)

def shader_update(prop):
    def updater(self, context):
        print("shader_update")
        if not hasattr(context, "material"):
            return
        mat = context.material
        if type(self) == MuTextureProperties:
            pass
        elif type(self) == MuMaterialProperties:
            if (prop) == "shader":
                create_nodes(mat)
            else:
                shader = ksp_shaders[mat.mumatprop.shader]
                nodes = mat.node_tree.nodes
                for s in shader:
                    if s[0] == "set" and s[3] == prop:
                        node_set(mat.name, mat.mumatprop, nodes, s)
                    elif s[0] == "settex" and s[3] == prop:
                        node_settex(mat.name, mat.mumatprop, nodes, s)
    return updater

def shader_items(self, context):
    slist = list(shader_properties.keys())
    slist.sort()
    enum = (('', "", ""),)
    enum += tuple(map(lambda s: (s, s, ""), slist))
    return enum

class IO_OBJECT_MU_MT_shader_presets(Menu):
    bl_label = "Shader Presets"
    bl_idname = "IO_OBJECT_MU_MT_shader_presets"
    preset_subdir = "io_object_mu/shaders"
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset


class IO_OBJECT_MU_OT_shader_presets(AddPresetBase, Operator):
    bl_idname = "io_object_mu.shader_presets"
    bl_label = "Shaders"
    bl_description = "Mu Shader Presets"
    preset_menu = "IO_OBJECT_MU_MT_shader_presets"
    preset_subdir = "io_object_mu/shaders"

    preset_defines = [
        "mat = bpy.context.material.mumatprop"
        ]
    preset_values = [
        "mat.name",
        "mat.shaderName",
        "mat.color",
        "mat.vector",
        "mat.float2",
        "mat.float3",
        "mat.texture",
        ]

# Draw into an existing panel
def panel_func(self, context):
    layout = self.layout

    row = layout.row(align=True)
    row.menu(OBJECT_MT_draw_presets.__name__, text=OBJECT_MT_draw_presets.bl_label)
    row.operator(AddPresetObjectDraw.bl_idname, text="", icon='ADD')
    row.operator(AddPresetObjectDraw.bl_idname, text="", icon='REMOVE').remove_active = True

class MuMaterialProperties(bpy.types.PropertyGroup):
    name: StringProperty(name="Name")
    shaderName: StringProperty(name="Shader")
    color: PointerProperty(type = MuMaterialColorPropertySet)
    vector: PointerProperty(type = MuMaterialVectorPropertySet)
    float2: PointerProperty(type = MuMaterialFloat2PropertySet)
    float3: PointerProperty(type = MuMaterialFloat3PropertySet)
    texture: PointerProperty(type = MuMaterialTexturePropertySet)

class OBJECT_UL_Property_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index):
        if item:
            layout.prop(item, "name", text="", emboss=False, icon_value=icon)
        else:
            layout.label(text="", icon_value=icon)

def draw_property_list(layout, propset, propsetname):
    box = layout.box()
    row = box.row()
    row.operator("object.mushaderprop_expand", text="",
                 icon='TRIA_DOWN' if propset.expanded else 'TRIA_RIGHT',
                 emboss=False).propertyset = propsetname
    row.label(text = propset.bl_label)
    row.label(text = "",
              icon = 'RADIOBUT_ON' if propset.properties else 'RADIOBUT_OFF')
    if propset.expanded:
        box.separator()
        row = box.row()
        col = row.column()
        col.template_list("OBJECT_UL_Property_list", "", propset, "properties", propset, "index")
        col = row.column(align=True)
        add_op = "object.mushaderprop_add"
        rem_op = "object.mushaderprop_remove"
        col.operator(add_op, icon='ADD', text="").propertyset = propsetname
        col.operator(rem_op, icon='REMOVE', text="").propertyset = propsetname
        if len(propset.properties) > propset.index >= 0:
            propset.draw_item(box)

class OBJECT_PT_MuMaterialPanel(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'material'
    bl_label = 'Mu Shader'

    @classmethod
    def poll(cls, context):
        return context.material != None

    def drawtex(self, layout, texprop):
        box = layout.box()
        box.prop(texprop, "tex")
        box.prop(texprop, "scale")
        box.prop(texprop, "offset")

    def draw(self, context):
        layout = self.layout
        matprops = context.material.mumatprop
        row = layout.row()
        col = row.column()
        r = col.row(align=True)
        r.menu("IO_OBJECT_MU_MT_shader_presets",
               text=IO_OBJECT_MU_OT_shader_presets.bl_label)
        r.operator("io_object_mu.shader_presets", text="", icon='ADD')
        r.operator("io_object_mu.shader_presets", text="", icon='REMOVE').remove_active = True
        col.prop(matprops, "name")
        col.prop(matprops, "shaderName")
        draw_property_list(layout, matprops.texture, "texture")
        draw_property_list(layout, matprops.color, "color")
        draw_property_list(layout, matprops.vector, "vector")
        draw_property_list(layout, matprops.float2, "float2")
        draw_property_list(layout, matprops.float3, "float3")

classes = (
    IO_OBJECT_MU_MT_shader_presets,
    IO_OBJECT_MU_OT_shader_presets,
    MuMaterialProperties,
    OBJECT_UL_Property_list,
    OBJECT_PT_MuMaterialPanel,
)
custom_properties = (
    (bpy.types.Material, "mumatprop", MuMaterialProperties),
)
