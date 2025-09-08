# ChatPS Modular Plugin System - Integration Plan

## Overview
Design and implement a modular plugin system for ChatPS_ng that allows loading modules from multiple directories and exposing them as tabs in the Streamlit interface.

## Architecture Design

### 1. Module Structure
```
/home/psadmin/ai/
├── ChatPS_v2_ng/
│   ├── modules/
│   │   ├── chatps_streamlit_ui.py (main UI)
│   │   └── [existing modules]
│   ├── plugins/                    # NEW: Plugin directory
│   │   ├── __init__.py
│   │   ├── registry.py            # Plugin registry
│   │   └── loader.py              # Dynamic loader
│   └── plugin_modules/            # NEW: External plugins
│       ├── virtual_mailroom/      # Symlink or copy
│       └── [future modules]/
│
├── virtual_mailroom/              # Original location
│   ├── __init__.py
│   ├── plugin_config.json        # Plugin metadata
│   └── mailroom_module.py        # Streamlit component
│
└── [other_ai_modules]/           # Future modules
```

### 2. Plugin Configuration Format
Each plugin module needs a `plugin_config.json`:

```json
{
  "name": "Virtual Mailroom",
  "version": "1.0.0",
  "description": "PDF processing and document routing system",
  "icon": "📬",
  "tab_order": 10,
  "enabled": true,
  "entry_point": "mailroom_module.py",
  "main_function": "render_mailroom_tab",
  "dependencies": [
    "PyPDF2",
    "pdfplumber"
  ],
  "settings": {
    "default_output_dir": "output",
    "enable_ai": true,
    "chatps_env": "nextgen"
  }
}
```

### 3. Plugin Registry System

```python
# plugins/registry.py
class PluginRegistry:
    def __init__(self):
        self.plugins = {}
        self.load_order = []
    
    def discover_plugins(self, directories):
        """Scan directories for plugin modules"""
        
    def register_plugin(self, plugin_info):
        """Register a plugin with metadata"""
        
    def get_enabled_plugins(self):
        """Return list of enabled plugins sorted by tab_order"""
        
    def load_plugin_module(self, plugin_name):
        """Dynamically import and return plugin module"""
```

### 4. Main UI Integration

```python
# Enhanced chatps_streamlit_ui.py structure
import streamlit as st
from plugins.registry import PluginRegistry

def main():
    st.set_page_config(page_title="ChatPS NG", layout="wide")
    
    # Initialize plugin registry
    registry = PluginRegistry()
    registry.discover_plugins([
        "/home/psadmin/ai/ChatPS_v2_ng/plugin_modules",
        "/home/psadmin/ai/virtual_mailroom",
        # Add more plugin directories
    ])
    
    # Get enabled plugins
    plugins = registry.get_enabled_plugins()
    
    # Create tabs dynamically
    tab_names = ["ChatPS Core"] + [p['name'] for p in plugins]
    tabs = st.tabs(tab_names)
    
    # Render core ChatPS in first tab
    with tabs[0]:
        render_chatps_core()
    
    # Render plugin tabs
    for i, plugin in enumerate(plugins, 1):
        with tabs[i]:
            module = registry.load_plugin_module(plugin['name'])
            if module:
                module.render_tab()
```

## Implementation Steps

### Phase 1: Create Plugin Infrastructure
1. **Create plugin directories**
   ```bash
   mkdir -p /home/psadmin/ai/ChatPS_v2_ng/plugins
   mkdir -p /home/psadmin/ai/ChatPS_v2_ng/plugin_modules
   ```

2. **Implement Plugin Registry**
   - Create `registry.py` with discovery mechanism
   - Create `loader.py` for dynamic imports
   - Add error handling and logging

3. **Create Plugin Base Class**
   ```python
   class ChatPSPlugin:
       def __init__(self, config):
           self.config = config
       
       def render_tab(self):
           """Override in subclass"""
           pass
       
       def get_settings(self):
           return self.config.get('settings', {})
   ```

### Phase 2: Adapt Virtual Mailroom

1. **Create Mailroom Plugin Module**
   ```python
   # virtual_mailroom/mailroom_module.py
   import streamlit as st
   from .pdf_splitter import PDFSplitter
   from .mailroom_chatps_integration import EnhancedVirtualMailroom
   
   def render_mailroom_tab():
       st.header("📬 Virtual Mailroom")
       
       # Add drag-and-drop uploader
       uploaded_files = st.file_uploader(
           "Drag and drop PDFs here",
           type=['pdf'],
           accept_multiple_files=True,
           key="mailroom_uploader"
       )
       
       # Document type selector
       doc_type = st.selectbox(
           "Document Type (Optional)",
           ["Auto-Detect", "REGF", "AFF", "ICD", "NOTICE", 
            "SUMMONS", "MOTION", "JUDGMENT", "OTHER"]
       )
       
       # Processing options
       col1, col2 = st.columns(2)
       with col1:
           use_ai = st.checkbox("Use AI Enhancement", value=True)
       with col2:
           pages_per_doc = st.number_input("Pages per Document", 
                                          min_value=0, value=0)
       
       # Process button
       if st.button("Process Documents"):
           process_uploaded_files(uploaded_files, doc_type, use_ai)
   ```

2. **Add Drag-and-Drop Support**
   - Use Streamlit's native file_uploader with drag-drop
   - Support multiple file selection
   - Show upload progress

3. **Enhanced Document Type Selection**
   - Dropdown with common types
   - Auto-detect option (default)
   - Remember last selection

### Phase 3: Integrate with ChatPS_ng

1. **Modify Main Streamlit UI**
   - Add plugin loading logic
   - Create dynamic tab generation
   - Maintain backward compatibility

2. **Create Plugin Loader Service**
   ```python
   # plugins/loader.py
   import importlib.util
   import sys
   from pathlib import Path
   
   class PluginLoader:
       @staticmethod
       def load_module(path, name):
           spec = importlib.util.spec_from_file_location(name, path)
           module = importlib.util.module_from_spec(spec)
           sys.modules[name] = module
           spec.loader.exec_module(module)
           return module
   ```

3. **Add Hot-Reload Support**
   - Watch for plugin changes
   - Reload without restart
   - Cache management

### Phase 4: Testing & Documentation

1. **Test Integration**
   - Load virtual mailroom as plugin
   - Verify tab switching
   - Test data flow between modules

2. **Create Developer Guide**
   - Plugin creation template
   - API documentation
   - Best practices

## Benefits

1. **Modularity**
   - Each feature in separate module
   - Easy to add/remove features
   - Independent development

2. **Scalability**
   - Add new modules without modifying core
   - Plugin marketplace potential
   - Community contributions

3. **Maintainability**
   - Clear separation of concerns
   - Easier debugging
   - Version management per module

4. **User Experience**
   - Unified interface
   - Consistent navigation
   - Feature discovery through tabs

## Next Steps

1. **Immediate Actions**
   - Create plugin infrastructure files
   - Adapt virtual mailroom for plugin architecture
   - Test with ChatPS_ng

2. **Short Term**
   - Add more modules (enfermera_elena, etc.)
   - Create plugin management UI
   - Add user preferences

3. **Long Term**
   - Plugin marketplace
   - User-created plugins
   - Cross-plugin communication

## Migration Path

### From Standalone to Plugin
1. Keep original virtual_mailroom intact
2. Create plugin wrapper
3. Test in both modes
4. Gradual migration

### Deployment Strategy
1. **Development** - Test plugin system
2. **NextGen** - Deploy with GPU support
3. **Production** - After validation

## Configuration Files Needed

### 1. Plugin Registry Config
```json
{
  "plugin_directories": [
    "/home/psadmin/ai/ChatPS_v2_ng/plugin_modules",
    "/home/psadmin/ai/virtual_mailroom"
  ],
  "auto_discover": true,
  "cache_enabled": true,
  "hot_reload": false
}
```

### 2. Virtual Mailroom Plugin Config
```json
{
  "name": "Virtual Mailroom",
  "version": "1.0.0",
  "description": "Intelligent PDF processing and document routing",
  "icon": "📬",
  "tab_order": 10,
  "enabled": true,
  "entry_point": "mailroom_module.py",
  "main_function": "render_mailroom_tab",
  "settings": {
    "default_output_dir": "output",
    "enable_ai": true,
    "chatps_env": "nextgen",
    "max_file_size_mb": 100,
    "allowed_extensions": ["pdf"],
    "enable_drag_drop": true,
    "show_document_types": true
  }
}
```

## Success Criteria

1. ✅ Virtual mailroom loads as tab in ChatPS_ng
2. ✅ Drag-and-drop PDF upload works
3. ✅ Document type selection available
4. ✅ Processing uses ChatPS API
5. ✅ Results display in unified interface
6. ✅ No impact on existing ChatPS functionality
7. ✅ Plugin can be enabled/disabled
8. ✅ Clear documentation for adding new plugins

## Risk Mitigation

1. **Performance Impact**
   - Lazy loading of plugins
   - Caching mechanisms
   - Resource monitoring

2. **Security Concerns**
   - Plugin sandboxing
   - Permission system
   - Code validation

3. **Compatibility Issues**
   - Version checking
   - Dependency management
   - Fallback mechanisms

This plan provides a clear path to integrate the virtual mailroom and future modules into ChatPS_ng as a unified, tabbed interface.