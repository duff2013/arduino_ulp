#   Copyright (c) 2018 Colin Duffy (https://github.com/duff2013)
#
#   Permission is hereby granted, free of charge, to any person obtaining a copy of this
#   software and associated documentation files (the "Software"), to deal in the Software
#   without restriction, including without limitation the rights to use, copy, modify, merge,
#   publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons
#   to whom the Software is furnished to do so, subject to the following conditions:
#
#   The above copyright notice and this permission notice shall be included in all copies or
#   substantial portions of the Software.
#
#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
#   INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
#   PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
#   FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
#   OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#   DEALINGS IN THE SOFTWARE.


import os
import sys
import glob
import argparse
import subprocess

CPREPROCESSOR_FLAGS = []

EXTRA_FLAGS = dict()
EXTRA_FLAGS['doitESP32devkitV1']    = os.path.join('variants','doitESP32devkitV1')
EXTRA_FLAGS['esp32']                = os.path.join('cores','esp32')
EXTRA_FLAGS['E']                    = '-E'
EXTRA_FLAGS['P']                    = '-P'
EXTRA_FLAGS['XC']                   = '-xc'
EXTRA_FLAGS['O']                    = '-o'
EXTRA_FLAGS['O+']                   = '-O'
EXTRA_FLAGS['I']                    = '-I'
EXTRA_FLAGS['A']                    = '-A'
EXTRA_FLAGS['T']                    = '-T'
EXTRA_FLAGS['G']                    = '-g'
EXTRA_FLAGS['F']                    = '-f'
EXTRA_FLAGS['S']                    = '-s'
EXTRA_FLAGS['BINARY']               = 'binary'
EXTRA_FLAGS['D__ASSEMBLER__']       = '-D__ASSEMBLER__'
EXTRA_FLAGS['DESP_PLATFORM']        = '-DESP_PLATFORM'
EXTRA_FLAGS['DMBEDTLS_CONFIG_FILE'] = os.path.join('-DMBEDTLS_CONFIG_FILE=mbedtls','esp_config.h')
EXTRA_FLAGS['DHAVE_CONFIG_H']       = '-DHAVE_CONFIG_H'
EXTRA_FLAGS['MT']                   = '-MT'
EXTRA_FLAGS['MMD']                  = '-MMD'
EXTRA_FLAGS['MP']                   = '-MP'
EXTRA_FLAGS['DWITH_POSIX']          = '-DWITH_POSIX'
EXTRA_FLAGS['INPUT_TARGET']         = '--input-target'
EXTRA_FLAGS['OUTPUT_TARGET']        = '--output-target'
EXTRA_FLAGS['ELF32_XTENSA_LE']      = 'elf32-xtensa-le'
EXTRA_FLAGS['BINARY_ARCH']          = '--binary-architecture'
EXTRA_FLAGS['XTENSA']               = 'xtensa'
EXTRA_FLAGS['RENAME_SECTION']       = '--rename-section'
EXTRA_FLAGS['EMBEDDED']             = '.data=.rodata.embedded'
EXTRA_FLAGS['CRU']                  = 'cru'
EXTRA_FLAGS['ELF32']                = 'elf32-esp32ulp'
EXTRA_FLAGS['POSIX']                = 'posix'

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', action='store')
    parser.add_argument('-p', action='store')
    parser.add_argument('-u', action='store')
    parser.add_argument('-x', action='store')
    parser.add_argument('-I', action='append')
    args, options = parser.parse_known_args()

    for item in args.I:
        CPREPROCESSOR_FLAGS.append('-I')
        CPREPROCESSOR_FLAGS.append(item)

    board_options = []
    for item in options:
        if item.startswith('--'):
            board_options.append(item[1:])

    bpath = args.b
    ppath = args.p
    upath = args.u
    xpath = args.x

    os.chdir(os.path.join(bpath, 'sketch'))
    ulp_files = glob.glob('*.s')

    if not ulp_files:
        print "No ULP Assembly File(s) Detected..."
        with open('ulp_main.ld',"w") as fld:
            fld.close()
    else:
        build_ulp(bpath, ppath, xpath, upath, ulp_files, board_options)
    sys.exit(0)


def build_ulp(build_path, platform_path, xtensa_path, ulp_path, ulp_sfiles, board_options):
    print 'ULP Assembly File(s) Detected: ' + ', '.join(ulp_sfiles)
    console_string = ''
    cmds = gen_cmds(os.path.join(platform_path, 'tools'))

    for file in ulp_sfiles:
        file = file.split('.')
        file_names = gen_file_names(file[0])

        ## Run each assembly file (foo.S) through C preprocessor
        cmd = gen_xtensa_preprocessor_cmd(build_path, xtensa_path, file, board_options)
        proc = subprocess.Popen(cmd[1],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,shell=False)
        (out, err) = proc.communicate()
        if err:
            error_string = cmd[0] + '\n' + err
            sys.exit(error_string)
        else:
            console_string += cmd[0] + '\n'

        ## Run preprocessed assembly sources through assembler
        cmd = gen_binutils_as_cmd(build_path, ulp_path, file, board_options)
        proc = subprocess.Popen(cmd[1],stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=False)
        (out, err) = proc.communicate()
        if err:
            error_string = cmd[0] + '\n' + err
            sys.exit(error_string)
        else:
            console_string += cmd[0] + '\n'

    ## Run linker script template through C preprocessor
    cmd = gen_xtensa_ld_cmd(build_path, platform_path, xtensa_path, ulp_sfiles, board_options)
    proc = subprocess.Popen(cmd[1],stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=False)
    (out, err) = proc.communicate()
    if err:
        error_string = cmd[0] + '\n' + err
        sys.exit(error_string)
    else:
        console_string += cmd[0] + '\n'

    ## Link object files into an output ELF file
    cmd = gen_binutils_ld_cmd(build_path, ulp_path, ulp_sfiles, board_options)
    proc = subprocess.Popen(cmd[1],stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=False)
    (out, err) = proc.communicate()
    if err:
        error_string = cmd[0] + '\n' + err
        sys.exit(error_string)
    else:
        console_string += cmd[0] + '\n'

    ## Generate list of global symbols
    cmd = gen_binutils_nm_cmd(build_path, ulp_path, ulp_sfiles, board_options)
    proc = subprocess.Popen(cmd[1],stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=False)
    (out, err) = proc.communicate()
    if err:
        error_string = cmd[0] + '\n' + err
        sys.exit(error_string)
    else:
        file_names_constant = gen_file_names_constant()
        with open(file_names_constant['sym'],"w") as fsym:
            fsym.write(out)
        console_string += cmd[0] + '\n'

    ## Create LD export script and header file
    cmd = gen_mapgen_cmd(build_path, platform_path, ulp_sfiles, board_options)
    proc = subprocess.Popen(cmd[1],stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=False)
    (out, err) = proc.communicate()
    if err:
        error_string = cmd[0] + '\n' + err
        sys.exit(error_string)
    else:
        console_string += cmd[0] + '\n'

    ## Add the generated binary to the list of binary files
    cmd = gen_binutils_objcopy_cmd(build_path, ulp_path, ulp_sfiles, board_options)
    proc = subprocess.Popen(cmd[1],stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=False)
    (out, err) = proc.communicate()
    if err:
        error_string = cmd[0] + '\n' + err
        sys.exit(error_string)
    else:
        console_string += cmd[0] + '\n'

    ## Add the generated binary to the list of binary files
    cmd = gen_xtensa_objcopy_cmd(build_path, xtensa_path, ulp_sfiles, board_options)
    proc = subprocess.Popen(cmd[1],stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=False)
    (out, err) = proc.communicate()
    if err:
        error_string = cmd[0] + '\n' + err
        sys.exit(error_string)
    else:
        console_string += cmd[0] + '\n'

    ## embed into arduino.ar
    cmd = gen_XTENSA_AR_cmd(build_path, xtensa_path, ulp_sfiles, board_options)
    proc = subprocess.Popen(cmd[1],stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=False)
    (out, err) = proc.communicate()
    if err:
        error_string = cmd[0] + '\n' + err
        sys.exit(error_string)
    else:
        console_string += cmd[0]
    #print "command 1: " + str(cmd[1])
    print console_string

    return 0

def gen_xtensa_preprocessor_cmd(build_path, compiler_path, file, board_options):
    #cmds = gen_cmds(platform_path)#gen_cmds(os.path.join(platform_path, 'tools'))
    cmds = gen_xtensa_cmds(compiler_path)
    file_names = gen_file_names(file[0])
    XTENSA_GCC_PREPROCESSOR = []
    XTENSA_GCC_PREPROCESSOR.append(cmds['XTENSA_GCC'])
    XTENSA_GCC_PREPROCESSOR.append(EXTRA_FLAGS['DESP_PLATFORM'])
    XTENSA_GCC_PREPROCESSOR.append(EXTRA_FLAGS['MMD'])
    XTENSA_GCC_PREPROCESSOR.append(EXTRA_FLAGS['MP'])
    XTENSA_GCC_PREPROCESSOR.append(EXTRA_FLAGS['DWITH_POSIX'])
    XTENSA_GCC_PREPROCESSOR.append(EXTRA_FLAGS['DMBEDTLS_CONFIG_FILE'])
    XTENSA_GCC_PREPROCESSOR.append(EXTRA_FLAGS['DHAVE_CONFIG_H'])
    XTENSA_GCC_PREPROCESSOR.append(EXTRA_FLAGS['MT'])
    XTENSA_GCC_PREPROCESSOR.append(file_names['o'])
    XTENSA_GCC_PREPROCESSOR.append(EXTRA_FLAGS['E'])
    XTENSA_GCC_PREPROCESSOR.append(EXTRA_FLAGS['P'])
    XTENSA_GCC_PREPROCESSOR.append(EXTRA_FLAGS['XC'])
    XTENSA_GCC_PREPROCESSOR.append(EXTRA_FLAGS['O'])
    XTENSA_GCC_PREPROCESSOR.append(file_names['ps'])
    XTENSA_GCC_PREPROCESSOR.extend(CPREPROCESSOR_FLAGS)
    XTENSA_GCC_PREPROCESSOR.extend(board_options)
    XTENSA_GCC_PREPROCESSOR.append(EXTRA_FLAGS['I'])
    XTENSA_GCC_PREPROCESSOR.append(os.path.join(build_path, 'sketch'))
    XTENSA_GCC_PREPROCESSOR.append(EXTRA_FLAGS['D__ASSEMBLER__'])
    XTENSA_GCC_PREPROCESSOR.append(file[0] + '.s')
    STR_CMD = ' '.join(XTENSA_GCC_PREPROCESSOR)
    return STR_CMD, XTENSA_GCC_PREPROCESSOR

def gen_binutils_as_cmd(build_path, compiler_path, file, board_options):
    #cmds = gen_cmds(os.path.join(platform_path, 'tools'))
    cmds = gen_ulp_cmds(compiler_path)
    file_names = gen_file_names(file[0])
    ULP_AS = []
    ULP_AS.append(cmds['ULP_AS'])
    ULP_AS.append('-al=' + file_names['lst'])
    ULP_AS.append(EXTRA_FLAGS['O'])
    ULP_AS.append(file_names['o'])
    ULP_AS.append(file_names['ps'])
    STR_CMD = ' '.join(ULP_AS)
    return STR_CMD, ULP_AS

def gen_xtensa_ld_cmd(build_path, platform_path, compiler_path, file, board_options):
    #cmds = gen_cmds(os.path.join(platform_path, 'tools'))
    cmds = gen_xtensa_cmds(compiler_path)
    file_names = gen_file_names_constant()
    XTENSA_GCC_LD = []
    XTENSA_GCC_LD.append(cmds['XTENSA_GCC'])
    XTENSA_GCC_LD.append(EXTRA_FLAGS['DESP_PLATFORM'])
    XTENSA_GCC_LD.append(EXTRA_FLAGS['MMD'])
    XTENSA_GCC_LD.append(EXTRA_FLAGS['MP'])
    XTENSA_GCC_LD.append(EXTRA_FLAGS['DWITH_POSIX'])
    XTENSA_GCC_LD.append(EXTRA_FLAGS['DMBEDTLS_CONFIG_FILE'])
    XTENSA_GCC_LD.append(EXTRA_FLAGS['DHAVE_CONFIG_H'])
    XTENSA_GCC_LD.append(EXTRA_FLAGS['MT'])
    XTENSA_GCC_LD.append(file_names['ld'])
    XTENSA_GCC_LD.append(EXTRA_FLAGS['E'])
    XTENSA_GCC_LD.append(EXTRA_FLAGS['P'])
    XTENSA_GCC_LD.append(EXTRA_FLAGS['XC'])
    XTENSA_GCC_LD.append(EXTRA_FLAGS['O'])
    XTENSA_GCC_LD.append(file_names['ld'])
    XTENSA_GCC_LD.extend(CPREPROCESSOR_FLAGS)
    XTENSA_GCC_LD.extend(board_options)
    XTENSA_GCC_LD.append(EXTRA_FLAGS['I'])
    XTENSA_GCC_LD.append(os.path.join(build_path, 'sketch'))
    XTENSA_GCC_LD.append(EXTRA_FLAGS['D__ASSEMBLER__'])
    XTENSA_GCC_LD.append(os.path.join(platform_path, 'tools', 'sdk', 'ld', 'esp32.ulp.ld'))
    STR_CMD = ' '.join(XTENSA_GCC_LD)
    return STR_CMD, XTENSA_GCC_LD

def gen_binutils_ld_cmd(build_path, compiler_path, file, board_options):
    #cmds = gen_cmds(os.path.join(platform_path, 'tools'))
    cmds = gen_ulp_cmds(compiler_path)
    file_names_constant = gen_file_names_constant()
    ULP_LD = []
    ULP_LD.append(cmds['ULP_LD'])
    ULP_LD.append(EXTRA_FLAGS['O'])
    ULP_LD.append(file_names_constant['elf'])
    ULP_LD.append(EXTRA_FLAGS['A'])
    ULP_LD.append(EXTRA_FLAGS['ELF32'])
    ULP_LD.append('-Map=' + file_names_constant['map'])
    ULP_LD.append(EXTRA_FLAGS['T'])
    ULP_LD.append(file_names_constant['ld'])
    for f in file:
        f = f.split('.')
        file_names = gen_file_names(f[0])
        ULP_LD.append(file_names['o'])
    STR_CMD = ' '.join(ULP_LD)
    return STR_CMD, ULP_LD

def gen_binutils_nm_cmd(build_path, compiler_path, file, board_options):
    #cmds = gen_cmds(os.path.join(platform_path, 'tools'))
    cmds = gen_ulp_cmds(compiler_path)
    file_names_constant = gen_file_names_constant()
    ULP_NM = []
    ULP_NM.append(cmds['ULP_NM'])
    ULP_NM.append(EXTRA_FLAGS['G'])
    ULP_NM.append(EXTRA_FLAGS['F'])
    ULP_NM.append(EXTRA_FLAGS['POSIX'])
    ULP_NM.append(file_names_constant['elf'])
    STR_CMD = ' '.join(ULP_NM)
    return STR_CMD, ULP_NM

def gen_mapgen_cmd(build_path, platform_path, file, board_options):
    cmds = gen_cmds(os.path.join(platform_path, 'tools'))
    file_names_constant = gen_file_names_constant()
    ULP_MAPGEN = []
    ULP_MAPGEN.append('python')
    ULP_MAPGEN.append(cmds['ULP_MAPGEN'])
    ULP_MAPGEN.append(EXTRA_FLAGS['S'])
    ULP_MAPGEN.append(file_names_constant['sym'])
    ULP_MAPGEN.append(EXTRA_FLAGS['O'])
    ULP_MAPGEN.append('ulp_main')
    STR_CMD = ' '.join(ULP_MAPGEN)
    return STR_CMD, ULP_MAPGEN

def gen_binutils_objcopy_cmd(build_path, compiler_path, file, board_options):
    #cmds = gen_cmds(os.path.join(platform_path, 'tools'))
    cmds = gen_ulp_cmds(compiler_path)
    file_names_constant = gen_file_names_constant()
    ULP_OBJCOPY = []
    ULP_OBJCOPY.append(cmds['ULP_OBJCPY'])
    ULP_OBJCOPY.append(EXTRA_FLAGS['O+'])
    ULP_OBJCOPY.append(EXTRA_FLAGS['BINARY'])
    ULP_OBJCOPY.append(file_names_constant['elf'])
    ULP_OBJCOPY.append(file_names_constant['bin'])
    STR_CMD = ' '.join(ULP_OBJCOPY)
    return STR_CMD, ULP_OBJCOPY

def gen_xtensa_objcopy_cmd(build_path, compiler_path, file, board_options):
    #cmds = gen_cmds(os.path.join(platform_path, 'tools'))
    cmds = gen_xtensa_cmds(compiler_path)
    file_names_constant = gen_file_names_constant()
    XTENSA_OBJCOPY = []
    XTENSA_OBJCOPY.append(cmds['XTENSA_OBJCPY'])
    XTENSA_OBJCOPY.append(EXTRA_FLAGS['INPUT_TARGET'])
    XTENSA_OBJCOPY.append(EXTRA_FLAGS['BINARY'])
    XTENSA_OBJCOPY.append(EXTRA_FLAGS['OUTPUT_TARGET'] )
    XTENSA_OBJCOPY.append(EXTRA_FLAGS['ELF32_XTENSA_LE'])
    XTENSA_OBJCOPY.append(EXTRA_FLAGS['BINARY_ARCH'])
    XTENSA_OBJCOPY.append(EXTRA_FLAGS['XTENSA'] )
    XTENSA_OBJCOPY.append(EXTRA_FLAGS['RENAME_SECTION'])
    XTENSA_OBJCOPY.append(EXTRA_FLAGS['EMBEDDED'])
    XTENSA_OBJCOPY.append(file_names_constant['bin'])
    XTENSA_OBJCOPY.append(file_names_constant['bin_o'])
    STR_CMD = ' '.join(XTENSA_OBJCOPY)
    return STR_CMD, XTENSA_OBJCOPY

def gen_XTENSA_AR_cmd(build_path, compiler_path, file, board_options):
    #cmds = gen_cmds(os.path.join(platform_path, 'tools'))
    cmds = gen_xtensa_cmds(compiler_path)
    file_names_constant = gen_file_names_constant()
    XTENSA_AR = []
    XTENSA_AR.append(cmds['XTENSA_AR'])
    XTENSA_AR.append(EXTRA_FLAGS['CRU'])
    XTENSA_AR.append(os.path.join(build_path, 'arduino.ar'))
    XTENSA_AR.append(file_names_constant['bin_o'])
    STR_CMD = ' '.join(XTENSA_AR)
    return STR_CMD, XTENSA_AR

def gen_file_names(sfile):
    file_names = dict();
    file_names['o']     = sfile + '.ulp.o'
    file_names['ps']    = sfile + '.ulp.pS'
    file_names['lst']   = sfile + '.ulp.lst'
    return file_names

def gen_file_names_constant():
    file_names = dict();
    file_names['ld']    = 'ulp_main.common.ld'
    file_names['elf']   = 'ulp_main.elf'
    file_names['map']   = 'ulp_main.map'
    file_names['sym']   = 'ulp_main.sym'
    file_names['bin']   = 'ulp_main.bin'
    file_names['bin_o'] = 'ulp_main.bin.bin.o'
    return file_names

def gen_cmds(path):
    cmds = dict();
    #cmds['XTENSA_GCC']    = os.path.join(path, 'xtensa-esp32-elf','bin','xtensa-esp32-elf-gcc')
    #cmds['XTENSA_OBJCPY'] = os.path.join(path, 'xtensa-esp32-elf','bin','xtensa-esp32-elf-objcopy')
    #cmds['XTENSA_AR']     = os.path.join(path, 'xtensa-esp32-elf','bin','xtensa-esp32-elf-ar')
    #cmds['ULP_AS']        = os.path.join(path, 'esp32ulp-elf-binutils','bin','esp32ulp-elf-as')
    #cmds['ULP_LD']        = os.path.join(path, 'esp32ulp-elf-binutils','bin','esp32ulp-elf-ld')
    #cmds['ULP_NM']        = os.path.join(path, 'esp32ulp-elf-binutils','bin','esp32ulp-elf-nm')
    #cmds['ULP_OBJCPY']    = os.path.join(path, 'esp32ulp-elf-binutils','bin','esp32ulp-elf-objcopy')
    cmds['ULP_MAPGEN']    = os.path.join(path, 'esp32ulp_mapgen.py')
    return cmds

def gen_xtensa_cmds(path):
    cmds = dict();
    cmds['XTENSA_GCC']    = os.path.join(path, 'xtensa-esp32-elf-gcc')
    cmds['XTENSA_OBJCPY'] = os.path.join(path, 'xtensa-esp32-elf-objcopy')
    cmds['XTENSA_AR']     = os.path.join(path, 'xtensa-esp32-elf-ar')
    return cmds

def gen_ulp_cmds(path):
    cmds = dict();
    cmds['ULP_AS']        = os.path.join(path, 'esp32ulp-elf-as')
    cmds['ULP_LD']        = os.path.join(path, 'esp32ulp-elf-ld')
    cmds['ULP_NM']        = os.path.join(path, 'esp32ulp-elf-nm')
    cmds['ULP_OBJCPY']    = os.path.join(path, 'esp32ulp-elf-objcopy')
    return cmds

if __name__ == '__main__':
    main(sys.argv[1:])
