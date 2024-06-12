# *****************************************************************************
#  This material contains trade secrets or otherwise confidential
#  information owned by Siemens Industry Software Inc. or its
#  affiliates (collectively, "Siemens"), or its licensors. Access to
#  and use of this information is strictly limited as set forth in the
#  Customer's applicable agreements with Siemens.
# 
#  Unpublished work. Copyright 2023 Siemens
# *****************************************************************************
import json

import AME


# Definitions of different application modes
SKETCH_MODE = "sketch_mode"
SUBMODEL_MODE = "submodel_mode"
PARAMETER_MODE = "parameter_mode"
SIMULATION_MODE = "simulation_mode"
NO_MODE = "no_mode"

"""
/brief Get the circuit used. The circuit can be found from an alias path
/param circuit[in/out] Circuit
/param alias_path [in] Path that can contain the circuit
/return circuit
"""
def _ensure_circuit(circuit=None, alias_path=None):
   """Ensure that we have a circuit
   """
   if alias_path and alias_path.count(":"):
      ignored_var, circuit = alias_path.split(":")

   if circuit is None:
      circuit = AME.AMEGetActiveCircuit()

   return circuit

"""
/brief Ensure that the circuit is in the right mode. If the circuit is in the wrong mode,
   it switches to the right mode
/param circuit [in] Circuit tested
/param mode [in] Required mode
"""
def _ensure_mode(circuit, mode):
   """Ensure we are in the given mode
   """
   AME._ensure_mode(circuit, mode)

# Start of generated code
def AMEAddComponent(icon_name, alias, position, snap_ports=True, circuit=None):
   circuit = _ensure_circuit(circuit)
   _ensure_mode(circuit, SKETCH_MODE)
   args = {}
   args['icon_name'] = str(icon_name) if icon_name != None else str('')
   args['alias'] = str(alias) if alias != None else str('')
   args['position.x'] = str(position[0])
   args['position.y'] = str(position[1])
   args['snap_ports'] = str(int(snap_ports))
   args['circuit'] = str(circuit)
   ret = AME.afp.set('add_component', json.dumps(args))
   return ret

def AMEAddDynamicComponent(icon_name, alias, dyn_param, position, snap_ports=True, circuit=None):
   circuit = _ensure_circuit(circuit)
   _ensure_mode(circuit, SKETCH_MODE)
   args = {}
   args['icon_name'] = str(icon_name) if icon_name != None else str('')
   args['alias'] = str(alias) if alias != None else str('')
   args['dyn_param'] = str(dyn_param) if dyn_param != None else str('')
   args['position.x'] = str(position[0])
   args['position.y'] = str(position[1])
   args['snap_ports'] = str(int(snap_ports))
   args['circuit'] = str(circuit)
   ret = AME.afp.set('add_dyn_component', json.dumps(args))
   return ret

def AMEAddInterfaceExportComponent(interface_type, alias, icon_text_line1, icon_text_line2, icon_text_line3, input_array, output_array, position, snap_ports=True, circuit=None):
   circuit = _ensure_circuit(circuit)
   _ensure_mode(circuit, SKETCH_MODE)
   args = {}
   args['interface_type'] = str(interface_type) if interface_type != None else str('')
   args['alias'] = str(alias) if alias != None else str('')
   args['icon_text_line1'] = str(icon_text_line1) if icon_text_line1 != None else str('')
   args['icon_text_line2'] = str(icon_text_line2) if icon_text_line2 != None else str('')
   args['icon_text_line3'] = str(icon_text_line3) if icon_text_line3 != None else str('')
   args['input_array'] = input_array
   args['output_array'] = output_array
   args['position.x'] = str(position[0])
   args['position.y'] = str(position[1])
   args['snap_ports'] = str(int(snap_ports))
   args['circuit'] = str(circuit)
   ret = AME.afp.set('add_interf_exp_component', json.dumps(args))
   return ret

def AMEAddInterfaceExportComponentWithSetupFile(interface_type, alias, setup_file_path, position, snap_ports=True, circuit=None):
   circuit = _ensure_circuit(circuit)
   _ensure_mode(circuit, SKETCH_MODE)
   args = {}
   args['interface_type'] = str(interface_type) if interface_type != None else str('')
   args['alias'] = str(alias) if alias != None else str('')
   args['setup_file_path'] = str(setup_file_path) if setup_file_path != None else str('')
   args['position.x'] = str(position[0])
   args['position.y'] = str(position[1])
   args['snap_ports'] = str(int(snap_ports))
   args['circuit'] = str(circuit)
   ret = AME.afp.set('add_interf_exp_component_with_setup_file', json.dumps(args))
   return ret

def AMEGetInterfaceInputsOutputsForModel(circuit=None):
   circuit = _ensure_circuit(circuit)
   _ensure_mode(circuit, SKETCH_MODE)
   args = {}
   args['circuit'] = str(circuit)
   ret = AME.afp.set('get_interf_io_for_model', json.dumps(args))
   ret = eval(ret)
   ret = tuple(ret)
   return ret

def AMESetInterfaceTypeForModel(interface_type, circuit=None):
   circuit = _ensure_circuit(circuit)
   _ensure_mode(circuit, SKETCH_MODE)
   args = {}
   args['interface_type'] = str(interface_type) if interface_type != None else str('')
   args['circuit'] = str(circuit)
   ret = AME.afp.set('set_interface_type_for_model', json.dumps(args))
   return ret

def AMEGetInterfaceTypeForModel(circuit=None):
   circuit = _ensure_circuit(circuit)
   _ensure_mode(circuit, SKETCH_MODE)
   args = {}
   args['circuit'] = str(circuit)
   ret = AME.afp.set('get_interface_type_for_model', json.dumps(args))
   return ret

def AMERemoveComponent(alias_path):
   circuit = _ensure_circuit(alias_path=alias_path)
   _ensure_mode(circuit, SKETCH_MODE)
   args = {}
   args['alias_path'] = str(alias_path)
   ret = AME.afp.set('remove_component', json.dumps(args))
   return ret

def AMEAddLine(alias, pfrom, pto, circuit=None):
   circuit = _ensure_circuit(circuit)
   _ensure_mode(circuit, SKETCH_MODE)
   args = {}
   args['alias'] = str(alias) if alias != None else str('')
   args['pfrom.x'] = str(pfrom[0])
   args['pfrom.y'] = str(pfrom[1])
   args['pto.x'] = str(pto[0])
   args['pto.y'] = str(pto[1])
   args['circuit'] = str(circuit)
   ret = AME.afp.set('add_line', json.dumps(args))
   return ret

def AMERemoveLine(alias_path):
   circuit = _ensure_circuit(alias_path=alias_path)
   _ensure_mode(circuit, SKETCH_MODE)
   args = {}
   args['alias_path'] = str(alias_path)
   ret = AME.afp.set('remove_line', json.dumps(args))
   return ret

def AMEAddSupercomponentPort(port_type, position, port_face, circuit=None):
   circuit = _ensure_circuit(circuit)
   args = {}
   args['port_type'] = str(port_type) if port_type != None else str('')
   args['position.x'] = str(position[0])
   args['position.y'] = str(position[1])
   args['port_face'] = str(port_face) if port_face != None else str('')
   args['circuit'] = str(circuit)
   ret = AME.afp.set('add_supercomponent_port', json.dumps(args))
   return ret

def AMEDisassembleSupercomponent(alias_name, scp_action="no_action"):
   args = {}
   args['alias_name'] = str(alias_name) if alias_name != None else str('')
   args['scp_action'] = str(scp_action) if scp_action != None else str('')
   ret = AME.afp.set('disassemble_supercomponent', json.dumps(args))
   ret = eval(ret)
   return ret

def AMEChangeSubmodel(alias_path, submodel_name, submodel_path=None, force_change=False, copy_common_parameters=False):
   circuit = _ensure_circuit(alias_path=alias_path)
   _ensure_mode(circuit, SKETCH_MODE)
   args = {}
   args['alias_path'] = str(alias_path)
   args['submodel_name'] = str(submodel_name) if submodel_name != None else str('')
   args['submodel_path'] = str(submodel_path) if submodel_path != None else str('')
   args['force_change'] = str(int(force_change))
   args['copy_common_parameters'] = str(int(copy_common_parameters))
   ret = AME.afp.set('change_submodel', json.dumps(args))
   return ret

def AMESetSupercomponentImage(image, circuit=None):
   circuit = _ensure_circuit(circuit)
   args = {}
   args['image'] = str(image) if image != None else str('')
   args['circuit'] = str(circuit)
   ret = AME.afp.set('set_supercomponent_image', json.dumps(args))
   return ret

def AMEFlipComponent(alias_path, snap_ports=True):
   args = {}
   args['alias_path'] = str(alias_path)
   args['snap_ports'] = str(int(snap_ports))
   ret = AME.afp.set('flip_component', json.dumps(args))
   return ret

def AMERotateComponent(alias_path, snap_ports=True):
   args = {}
   args['alias_path'] = str(alias_path)
   args['snap_ports'] = str(int(snap_ports))
   ret = AME.afp.set('rotate_component', json.dumps(args))
   return ret

def AMESetParameterValue(data_path, value):
   args = {}
   args['data_path'] = str(data_path)
   args['value'] = str(value) if value != None else str('')
   ret = AME.afp.set('data_value', json.dumps(args))
   return ret

def AMESetParameterDefaultValue(data_path):
   args = {}
   args['data_path'] = str(data_path)
   ret = AME.afp.set('data_default_value', json.dumps(args))
   return ret

def AMEMoveComponent(alias_path, position, snap_ports=True):
   args = {}
   args['alias_path'] = str(alias_path)
   args['position.x'] = str(position[0])
   args['position.y'] = str(position[1])
   args['snap_ports'] = str(int(snap_ports))
   ret = AME.afp.set('move_component', json.dumps(args))
   return ret

def AMEConnectComponentToLine(alias_path, comp_port, line_alias_path, line_port):
   circuit = _ensure_circuit(alias_path=alias_path)
   _ensure_mode(circuit, SKETCH_MODE)
   args = {}
   args['alias_path'] = str(alias_path)
   args['comp_port'] = str(comp_port)
   args['line_alias_path'] = str(line_alias_path)
   args['line_port'] = str(line_port)
   ret = AME.afp.set('connect_comp_2_line', json.dumps(args))
   return ret

def AMESetPortName(port_id, name, circuit=None):
   circuit = _ensure_circuit(circuit)
   args = {}
   args['port_id'] = str(port_id) if port_id != None else str('')
   args['name'] = str(name) if name != None else str('')
   args['circuit'] = str(circuit)
   ret = AME.afp.set('set_port_name', json.dumps(args))
   return ret

def AMEGetSelectedItems(circuit=None):
   circuit = _ensure_circuit(circuit)
   args = {}
   args['circuit'] = str(circuit)
   ret = AME.afp.set('get_selected_items', json.dumps(args))
   ret = eval(ret)
   return ret

def AMEGetComponentIcon(alias_path, accept_reverse=False, circuit=None):
   circuit = _ensure_circuit(circuit)
   args = {}
   args['alias_path'] = str(alias_path)
   args['accept_reverse'] = str(int(accept_reverse))
   args['circuit'] = str(circuit)
   ret = AME.afp.set('get_component_icon', json.dumps(args))
   return ret

def AMEGetComponentIconTransformation(alias_path, circuit=None):
   circuit = _ensure_circuit(circuit)
   args = {}
   args['alias_path'] = str(alias_path)
   args['circuit'] = str(circuit)
   ret = AME.afp.set('get_component_icon_transformation', json.dumps(args))
   return ret

def AMEAddBusCreator(alias, inputs, position, snap_ports=True, circuit=None):
   circuit = _ensure_circuit(circuit)
   _ensure_mode(circuit, SKETCH_MODE)
   args = {}
   args['alias'] = str(alias) if alias != None else str('')
   args['inputs'] = inputs
   args['position.x'] = str(position[0])
   args['position.y'] = str(position[1])
   args['snap_ports'] = str(int(snap_ports))
   args['circuit'] = str(circuit)
   ret = AME.afp.set('add_bus_creator', json.dumps(args))
   return ret

def AMEAddBusSelector(alias, outputs, position, snap_ports=True, circuit=None):
   circuit = _ensure_circuit(circuit)
   _ensure_mode(circuit, SKETCH_MODE)
   args = {}
   args['alias'] = str(alias) if alias != None else str('')
   args['outputs'] = outputs
   args['position.x'] = str(position[0])
   args['position.y'] = str(position[1])
   args['snap_ports'] = str(int(snap_ports))
   args['circuit'] = str(circuit)
   ret = AME.afp.set('add_bus_selector', json.dumps(args))
   return ret

def AMEAddBusJunction(alias, position, snap_ports=True, circuit=None):
   circuit = _ensure_circuit(circuit)
   _ensure_mode(circuit, SKETCH_MODE)
   args = {}
   args['alias'] = str(alias) if alias != None else str('')
   args['position.x'] = str(position[0])
   args['position.y'] = str(position[1])
   args['snap_ports'] = str(int(snap_ports))
   args['circuit'] = str(circuit)
   ret = AME.afp.set('add_bus_junction', json.dumps(args))
   return ret

def AMEModifyBusCreator(alias_path, inputs):
   circuit = _ensure_circuit(alias_path=alias_path)
   _ensure_mode(circuit, SKETCH_MODE)
   args = {}
   args['alias_path'] = str(alias_path)
   args['inputs'] = inputs
   ret = AME.afp.set('modify_bus_creator', json.dumps(args))
   return ret

def AMEModifyBusSelector(alias_path, outputs):
   circuit = _ensure_circuit(alias_path=alias_path)
   _ensure_mode(circuit, SKETCH_MODE)
   args = {}
   args['alias_path'] = str(alias_path)
   args['outputs'] = outputs
   ret = AME.afp.set('modify_bus_selector', json.dumps(args))
   return ret

def AMEEditDynamicComponent(alias_path, dyn_param, circuit=None):
   circuit = _ensure_circuit(circuit)
   _ensure_mode(circuit, SKETCH_MODE)
   args = {}
   args['alias_path'] = str(alias_path) if alias_path != None else str('')
   args['dyn_param'] = str(dyn_param) if dyn_param != None else str('')
   args['circuit'] = str(circuit)
   ret = AME.afp.set('edit_dyn_component', json.dumps(args))
   return ret

def AMESetElementAlias(alias, new_alias, circuit=None):
   circuit = _ensure_circuit(circuit)
   _ensure_mode(circuit, SKETCH_MODE)
   args = {}
   args['alias'] = str(alias) if alias != None else str('')
   args['new_alias'] = str(new_alias) if new_alias != None else str('')
   args['circuit'] = str(circuit)
   ret = AME.afp.set('set_element_alias', json.dumps(args))
   ret = eval(ret)
   return ret

def AMECenterComponent(alias_path):
   args = {}
   args['alias_path'] = str(alias_path)
   ret = AME.afp.set('ame_center_component', json.dumps(args))
   return ret

def AMESetElementColor(alias_path, color):
   args = {}
   args['alias_path'] = str(alias_path)
   args['color'] = str(color) if color != None else str('')
   ret = AME.afp.set('set_element_color', json.dumps(args))
   return ret

def AMEGetElementColor(alias_path):
   args = {}
   args['alias_path'] = str(alias_path)
   ret = AME.afp.set('get_element_color', json.dumps(args))
   return ret

def AMERemoveSupercomponentPort(port_id, circuit=None):
   circuit = _ensure_circuit(circuit)
   _ensure_mode(circuit, SKETCH_MODE)
   args = {}
   args['port_id'] = str(port_id) if port_id != None else str('')
   args['circuit'] = str(circuit)
   ret = AME.afp.set('remove_supercomponent_port', json.dumps(args))
   return ret

def AMESetPortTag(alias_path, port_number, port_tag):
   args = {}
   args['alias_path'] = str(alias_path)
   args['port_number'] = str(port_number)
   args['port_tag'] = str(port_tag) if port_tag != None else str('')
   ret = AME.afp.set('set_port_tag', json.dumps(args))
   return ret

def AMEAttachAppToSupercomponent(app_path, parameter_mode, simulation_mode, circuit, app_name=""):
   circuit = _ensure_circuit(circuit)
   _ensure_mode(circuit, SKETCH_MODE)
   args = {}
   args['app_path'] = str(app_path) if app_path != None else str('')
   args['parameter_mode'] = str(int(parameter_mode))
   args['simulation_mode'] = str(int(simulation_mode))
   args['circuit'] = str(circuit)
   args['app_name'] = str(app_name) if app_name != None else str('')
   ret = AME.afp.set('attach_app_to_supercomponent', json.dumps(args))
   return ret

def AMEAttachPlotConfigurationToSupercomponent(plot_configuration_path, circuit, my_plot_name=""):
   circuit = _ensure_circuit(circuit)
   _ensure_mode(circuit, SKETCH_MODE)
   args = {}
   args['plot_configuration_path'] = str(plot_configuration_path) if plot_configuration_path != None else str('')
   args['circuit'] = str(circuit)
   args['my_plot_name'] = str(my_plot_name) if my_plot_name != None else str('')
   ret = AME.afp.set('attach_plot_configuration_to_supercomponent', json.dumps(args))
   return ret

def AMEGetDynamicParamValues(alias_path):
   circuit = _ensure_circuit(alias_path=alias_path)
   _ensure_mode(circuit, SKETCH_MODE)
   args = {}
   args['alias_path'] = str(alias_path)
   ret = AME.afp.set('get_dynamic_param_values', json.dumps(args))
   ret = eval(ret)
   return ret

def AMEGetBusVariablesUsage(alias_path, port_number):
   args = {}
   args['alias_path'] = str(alias_path)
   args['port_number'] = str(port_number)
   ret = AME.afp.set('get_bus_variables_usage', json.dumps(args))
   ret = eval(ret)
   ret = tuple(ret)
   return ret

def AMEGetCompParVarList(data_path, circuit=None):
   circuit = _ensure_circuit(circuit)
   args = {}
   args['data_path'] = str(data_path) if data_path != None else str('')
   args['circuit'] = str(circuit)
   ret = AME.afp.set('get_comp_par_var_list', json.dumps(args))
   return ret

def AMEGetActiveSketch(circuit=None):
   circuit = _ensure_circuit(circuit)
   args = {}
   args['circuit'] = str(circuit)
   ret = AME.afp.set('get_active_sketch', json.dumps(args))
   return ret

def AMEIsTunableParameter(data_path):
   args = {}
   args['data_path'] = str(data_path) if data_path != None else str('')
   ret = AME.afp.set('is_tunable_parameter', json.dumps(args))
   ret = eval(ret)
   return ret

def AMEGetLinkedVariable(data_path):
   args = {}
   args['data_path'] = str(data_path) if data_path != None else str('')
   ret = AME.afp.set('get_linked_variable', json.dumps(args))
   return ret

def AMESetRunParameter(parameter_name, value, circuit=None):
   circuit = _ensure_circuit(circuit)
   _ensure_mode(circuit, SIMULATION_MODE)
   args = {}
   args['parameter_name'] = str(parameter_name) if parameter_name != None else str('')
   args['value'] = str(value) if value != None else str('')
   args['circuit'] = str(circuit)
   ret = AME.afp.set('set_run_parameter', json.dumps(args))
   return ret

def AMESetLAStatus(data_path, value, circuit=None):
   circuit = _ensure_circuit(circuit)
   args = {}
   args['data_path'] = str(data_path) if data_path != None else str('')
   args['value'] = str(value) if value != None else str('')
   args['circuit'] = str(circuit)
   ret = AME.afp.set('set_la_status', json.dumps(args))
   return ret

def AMESaveVariable(data_path, save_next, circuit=None):
   circuit = _ensure_circuit(circuit)
   _ensure_mode(circuit, PARAMETER_MODE)
   args = {}
   args['data_path'] = str(data_path) if data_path != None else str('')
   args['save_next'] = str(int(save_next))
   args['circuit'] = str(circuit)
   ret = AME.afp.set('set_save_next_variable', json.dumps(args))
   ret = eval(ret)
   return ret

def AMEIsSavedVariable(data_path, circuit=None):
   circuit = _ensure_circuit(circuit)
   _ensure_mode(circuit, PARAMETER_MODE)
   args = {}
   args['data_path'] = str(data_path) if data_path != None else str('')
   args['circuit'] = str(circuit)
   ret = AME.afp.set('is_saved_next_variable', json.dumps(args))
   ret = eval(ret)
   return ret

def AMEGetCommercialVersionName():
   args = {}
   ret = AME.afp.set('get_commercial_version_name', json.dumps(args))
   return ret

def AMEAddPathsToPathList(paths_to_add):
   args = {}
   args['paths_to_add'] = paths_to_add
   ret = AME.afp.set('add_paths_to_path_list', json.dumps(args))
   return ret

def AMERemovePathsFromPathList(paths_to_remove):
   args = {}
   args['paths_to_remove'] = paths_to_remove
   ret = AME.afp.set('remove_paths_from_path_list', json.dumps(args))
   return ret

def AMERebuildCategoryPathList():
   args = {}
   ret = AME.afp.set('rebuild_category_path_list', json.dumps(args))
   return ret

def AMEGetPathList():
   args = {}
   ret = AME.afp.set('get_path_list', json.dumps(args))
   ret = eval(ret)
   return ret

def AMEActivatePathsInPathList(paths_to_activate):
   args = {}
   args['paths_to_activate'] = paths_to_activate
   ret = AME.afp.set('activate_paths_in_path_list', json.dumps(args))
   return ret

def AMEDeactivatePathsInPathList(paths_to_deactivate):
   args = {}
   args['paths_to_deactivate'] = paths_to_deactivate
   ret = AME.afp.set('deactivate_paths_in_path_list', json.dumps(args))
   return ret

def AMEGetActivePathsInPathList():
   args = {}
   ret = AME.afp.set('get_active_paths_in_path_list', json.dumps(args))
   ret = eval(ret)
   return ret

def AMEGetNetworkList(circuit=None):
   circuit = _ensure_circuit(circuit)
   args = {}
   args['circuit'] = str(circuit)
   ret = AME.afp.set('get_network_list', json.dumps(args))
   ret = eval(ret)
   return ret

def AMEGetSubmodelNetworkInstanceList(alias_path, circuit=None):
   circuit = _ensure_circuit(circuit)
   args = {}
   args['alias_path'] = str(alias_path)
   args['circuit'] = str(circuit)
   ret = AME.afp.set('get_submodel_network_instance_list', json.dumps(args))
   ret = eval(ret)
   return ret

def AMEGetSupercomponentPortLabel(port_index, circuit):
   circuit = _ensure_circuit(circuit)
   args = {}
   args['port_index'] = str(port_index)
   args['circuit'] = str(circuit)
   ret = AME.afp.set('get_supercomponent_port_label', json.dumps(args))
   return ret

def AMESenseInternalVariables(alias_path, sense_variables, circuit=None):
   circuit = _ensure_circuit(circuit)
   args = {}
   args['alias_path'] = str(alias_path)
   args['sense_variables'] = sense_variables
   args['circuit'] = str(circuit)
   ret = AME.afp.set('action_sense_internal_variables', json.dumps(args))
   return ret

def AMEUnSenseInternalVariables(alias_path, circuit=None):
   circuit = _ensure_circuit(circuit)
   args = {}
   args['alias_path'] = str(alias_path)
   args['circuit'] = str(circuit)
   ret = AME.afp.set('action_unsense_internal_variables', json.dumps(args))
   return ret

def AMEGetSensedInternalVariables(alias_path, circuit=None):
   circuit = _ensure_circuit(circuit)
   args = {}
   args['alias_path'] = str(alias_path)
   args['circuit'] = str(circuit)
   ret = AME.afp.set('api_get_sensed_internal_variables', json.dumps(args))
   ret = eval(ret)
   return ret

def AMEOpenSketchGenerationWizard(file_path=None, applications_path=None, keep_ratio=True, clear_sketch=True, circuit=None):
   circuit = _ensure_circuit(circuit)
   _ensure_mode(circuit, SKETCH_MODE)
   args = {}
   args['file_path'] = str(file_path) if file_path != None else str('')
   args['applications_path'] = str(applications_path) if applications_path != None else str('')
   args['keep_ratio'] = str(int(keep_ratio))
   args['clear_sketch'] = str(int(clear_sketch))
   args['circuit'] = str(circuit)
   ret = AME.afp.set('open_sketch_generation_wizard', json.dumps(args))
   return ret

def AMEAddGlobalParameter(gp_type, name=None, title=None, value=None, enumeration_values=None, parent_group_id=None, position=None, sc_alias_path=None, gp_unit=None):
   circuit = _ensure_circuit(None)
   _ensure_mode(circuit, PARAMETER_MODE)
   args = {}
   args['gp_type'] = str(gp_type) if gp_type != None else str('')
   args['name'] = str(name) if name != None else str('')
   args['title'] = str(title) if title != None else str('')
   args['value'] = str(value) if value != None else str('')
   args['enumeration_values'] = enumeration_values
   args['parent_group_id'] = str(parent_group_id) if parent_group_id != None else str('')
   args['position'] = str(position) if position != None else str('')
   args['sc_alias_path'] = str(sc_alias_path) if sc_alias_path != None else str('')
   args['gp_unit'] = str(gp_unit) if gp_unit != None else str('')
   ret = AME.afp.set('add_global_parameter', json.dumps(args))
   return ret

# End of generated code
