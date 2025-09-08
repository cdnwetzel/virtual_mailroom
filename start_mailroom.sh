#!/bin/bash

echo "=================================="
echo "Virtual Mailroom System Launcher"
echo "=================================="
echo ""

show_menu() {
    echo "Select operation mode:"
    echo "1) Simple PDF Splitter (no AI)"
    echo "2) PDF Splitter with ChatPS Integration" 
    echo "3) Web Dashboard (Streamlit)"
    echo "4) Batch Processing"
    echo "5) Test ChatPS Connection"
    echo "6) Exit"
    echo ""
}

while true; do
    show_menu
    read -p "Enter choice [1-6]: " choice
    
    case $choice in
        1)
            echo "Starting PDF Splitter..."
            echo "Usage: python3 pdf_splitter.py <input.pdf> [options]"
            echo ""
            echo "Examples:"
            echo "  python3 pdf_splitter.py input.pdf"
            echo "  python3 pdf_splitter.py input.pdf -p 1  # NJ format"
            echo "  python3 pdf_splitter.py input.pdf -p 2  # NY format"
            echo "  python3 pdf_splitter.py input.pdf -t REGF"
            echo ""
            read -p "Enter command: " cmd
            $cmd
            ;;
            
        2)
            echo "Starting PDF Splitter with ChatPS..."
            echo ""
            echo "Select ChatPS environment:"
            echo "  1) Production (port 8501)"
            echo "  2) Development (port 8502)"
            echo "  3) NextGen GPU (port 8503)"
            read -p "Enter choice [1-3]: " env_choice
            
            case $env_choice in
                1) ENV="production" ;;
                2) ENV="development" ;;
                3) ENV="nextgen" ;;
                *) ENV="nextgen" ;;
            esac
            
            python3 mailroom_chatps_integration.py --env $ENV --test
            ;;
            
        3)
            echo "Starting Web Dashboard..."
            echo "Opening browser at http://localhost:8510"
            streamlit run mailroom_web.py --server.port 8510
            ;;
            
        4)
            echo "Batch Processing Mode"
            read -p "Enter input directory [input]: " input_dir
            input_dir=${input_dir:-input}
            
            read -p "Enter output directory [output]: " output_dir
            output_dir=${output_dir:-output}
            
            echo "Processing all PDFs in $input_dir..."
            for pdf in "$input_dir"/*.pdf; do
                if [ -f "$pdf" ]; then
                    echo "Processing: $(basename "$pdf")"
                    python3 pdf_splitter.py "$pdf" -o "$output_dir"
                fi
            done
            echo "Batch processing complete!"
            ;;
            
        5)
            echo "Testing ChatPS Connection..."
            python3 -c "
import requests
import sys

environments = {
    'Production': 'http://localhost:8501',
    'Development': 'http://localhost:8502',
    'NextGen': 'http://localhost:8503',
    'GPU Service': 'http://localhost:8504'
}

print('Checking ChatPS services...\n')

for name, url in environments.items():
    try:
        response = requests.get(f'{url}/health', timeout=2)
        if response.status_code == 200:
            print(f'✅ {name:12} - ONLINE at {url}')
        else:
            print(f'⚠️  {name:12} - RESPONDING but unhealthy')
    except:
        print(f'❌ {name:12} - OFFLINE')

print('\nRecommended: Use NextGen (8503) for GPU acceleration')
"
            ;;
            
        6)
            echo "Exiting..."
            exit 0
            ;;
            
        *)
            echo "Invalid choice. Please try again."
            ;;
    esac
    
    echo ""
    read -p "Press Enter to continue..."
    clear
done