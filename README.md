# Instalar dependências
sudo apt update
sudo apt install -y git zip unzip openjdk-11-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev

# Instalar buildozer
pip install buildozer

# Criar buildozer.spec (se não tiver)
buildozer init

# Compilar APK
buildozer android debug
