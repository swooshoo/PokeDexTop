# build_exe.py
import os
import platform
import PyInstaller.__main__

# Determine the system
system = platform.system()

# Get the platform-specific options
if system == 'Windows':
    icon_file = 'pokeball.ico'
    output_name = 'PokemonDashboard.exe'
elif system == 'Darwin':  # macOS
    icon_file = 'pokeball.icns'
    output_name = 'PokemonDashboard'
else:  # Linux
    icon_file = 'pokeball.png'
    output_name = 'PokemonDashboard'

# Check if icon file exists, otherwise use default
icon_path = os.path.join('assets', icon_file)
if not os.path.exists(icon_path):
    icon_path = None

# Define PyInstaller command arguments
args = [
    'pokemon_desktop_app.py',  # Your script name
    '--name=%s' % output_name,
    '--onefile',
    '--windowed',
    '--add-data=assets;assets',  # Include assets folder (Windows format)
]

# Adjust path separator for non-Windows platforms
if system != 'Windows':
    args[-1] = '--add-data=assets:assets'  # Unix format uses colon

# Add icon if available
if icon_path:
    args.append('--icon=%s' % icon_path)

# Run PyInstaller
PyInstaller.__main__.run(args)

print(f"Build complete! Executable created in ./dist/{output_name}")