{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    # Python and packages
    python313
    python313Packages.pip
    python313Packages.virtualenv
    python313Packages.pyside6
    python313Packages.pillow
    python313Packages.geopy
    python313Packages.python-dateutil
    python313Packages.requests

    # Qt6 dependencies for PySide6
    qt6.full
    qt6.qtbase
    qt6.qttools

    # System libraries that PySide6 and other packages might need
    libGL
    libxkbcommon
    fontconfig
    freetype

    # C++ standard library and GCC runtime
    stdenv.cc.cc.lib
    gcc-unwrapped.lib

    # X11 libraries for GUI applications
    xorg.libX11
    xorg.libXext
    xorg.libXrender
    xorg.libXi
    xorg.libXrandr
    xorg.libXcursor
    xorg.libXinerama
    xorg.libXxf86vm

    # Wayland support (if using Wayland)
    wayland

    # Additional libraries that might be needed
    glib
    cairo
    pango
    gdk-pixbuf
    gtk3
  ];

  shellHook = ''
    echo "Photo Metadata Editor Development Environment"
    echo "============================================="
    echo ""
    echo "Setting up Python virtual environment..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
      python -m venv venv
      echo "Created virtual environment"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    echo "Activated virtual environment"
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install only the packages not available in nixpkgs
    if [ ! -f "venv/.requirements_installed" ]; then
      echo "Installing additional Python dependencies..."
      pip install piexif
      touch venv/.requirements_installed
      echo "Dependencies installed successfully"
    else
      echo "Dependencies already installed"
    fi
    
    echo ""
    echo "Environment ready! You can now run:"
    echo "  python photo_metadata_editor_qt.py"
    echo ""
    echo "To exit the environment, type 'exit' or press Ctrl+D"
  '';

  # Environment variables
  QT_QPA_PLATFORM_PLUGIN_PATH = "${pkgs.qt6.qtbase}/lib/qt-6/plugins";
  QT_PLUGIN_PATH = "${pkgs.qt6.qtbase}/lib/qt-6/plugins";
  
  # Ensure Qt can find the platform plugins and system libraries
  LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
    pkgs.qt6.qtbase
    pkgs.libGL
    pkgs.libxkbcommon
    pkgs.fontconfig
    pkgs.freetype
    pkgs.xorg.libX11
    pkgs.xorg.libXext
    pkgs.xorg.libXrender
    pkgs.wayland
    pkgs.stdenv.cc.cc.lib
    pkgs.gcc-unwrapped.lib
    pkgs.glib
    pkgs.cairo
    pkgs.pango
    pkgs.gdk-pixbuf
    pkgs.gtk3
    pkgs.xorg.libXi
    pkgs.xorg.libXrandr
    pkgs.xorg.libXcursor
    pkgs.xorg.libXinerama
    pkgs.xorg.libXxf86vm
  ];
}
