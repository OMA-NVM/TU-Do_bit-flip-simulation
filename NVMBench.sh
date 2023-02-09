#!/bin/bash

export ROOT_DIR=$(pwd)

#build Gem5 with nvmain
buildgem5() {
    git submodule init
    git submodule update
    cd $ROOT_DIR/simulator/gem5
    scons -j 8 EXTRAS=../nvmain ./build/ARM/gem5.fast
    cd $ROOT_DIR
}

#Config App
config() {
    echo "Building $1"
    cd $ROOT_DIR/unikraft_setup/apps/$1
    make menuconfig
    cd $ROOT_DIR
}

#Build App
build() {
    echo "Building $1"
    cd $ROOT_DIR/unikraft_setup/apps/$1
    rm -r build
    make
    cd $ROOT_DIR
}

#Start the simulation of App in background and disowns it.
simulate() {
    #Create directory for simulation
    cd $ROOT_DIR/results
    rm -r $1.d
    mkdir $1.d
    cd $1.d
    #Move app binary to directory
    cp $ROOT_DIR/unikraft_setup/apps/$1/build/$1_gem5-arm64.dbg $1_gem5-arm64.dbg
    #Move trace config to directory
    #cp ../../BenchGem5NVMain/nvmain/Config/printtrace.config printtrace.config

    #Start simulation
    export M5_PATH=.
    nohup $ROOT_DIR/simulator/gem5/build/ARM/gem5.fast $ROOT_DIR/simulator/gem5/configs/example/fs.py \
    --bare-metal --disk-image $ROOT_DIR/simulator/fake.iso \
    --kernel=$ROOT_DIR/results/$1.d/$1_gem5-arm64.dbg \
    --nvmain-config=$ROOT_DIR/simulator/nvmain/Config/printtrace.config \
    --cpu-type=DerivO3CPU --machine-type=VExpress_GEM5_V2 --caches --l2cache \
    --l1i_size='32kB' --l1d_size='8kB' --l2_size='8kB' --dtb-filename=none \
    --mem-size=4GB > gem5.terminal &
    disown $(jobs -p)
    cd $ROOT_DIR
}

case $1 in
    init)
        buildgem5
    ;;
    config | c)
        config $2
    ;;
    build | b)
        build $2
    ;;
    simulate | s)
        simulate $2
    ;;
    bs)
        build $2
        simulate $2
    ;;
    * | help)
        if [ "$1" = "help" ]; then
          echo "Printing help screen"
        elif [ $1 ]; then
            echo "Unknown argument: $1"
        fi
        echo "Script to build and start the NVM Benchmark suite:"
        echo
        echo "  init                       Initialise this setup by building Gem5"
        echo "  config | c Name            Menuconfig benchmark with name NAME."
        echo "  build | b Name             Build benchmark with name NAME."
        echo "  simulate | s NAME          Simulate benchmark with name NAME."
        echo "  bs NAME                    Build and Simulate in one command"
        exit
    ;;
esac
