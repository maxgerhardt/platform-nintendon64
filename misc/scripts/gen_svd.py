import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from dataclasses import dataclass, field
from typing import List

# Define the Field class as a dataclass
@dataclass
class Field:
    name: str
    description: str
    bitOffset: int
    bitWidth: int

# Define the Register class as a dataclass
@dataclass
class Register:
    name: str
    description: str
    addressOffset: int
    size: int
    access: str
    fields: List[Field]

    def calculate_size(self):
        return self.addressOffset + self.size

# Define the Peripheral class as a dataclass
@dataclass
class Peripheral:
    name: str
    description: str
    baseAddress: str
    registers: List[Register]

    def calculate_size_of_registers(self):
        return max([register.calculate_size() for register in self.registers])

# Define the SI registers (using the previous method)
si_registers = [
    Register(
        name="SI_DRAM_ADDR",
        description="Serial Interface DRAM Address",
        addressOffset=0x0000,
        size=32,
        access="read-write",
        fields=[
            Field(name="DRAM_ADDR", description="RDRAM address used in SI DMAs", bitOffset=0, bitWidth=24)
        ]
    ),
    Register(
        name="SI_PIF_AD_RD64B",
        description="Serial Interface PIF Address Read (64-bit)",
        addressOffset=0x0004,
        size=32,
        access="read-only",
        fields=[
            Field(name="PIF_ADDR", description="Offset in PIF_RAM/PIF_ROM where to fetch data", bitOffset=0, bitWidth=11)
        ]
    ),
    Register(
        name="SI_PIF_AD_WR4B",
        description="Serial Interface PIF Address Write (4-byte)",
        addressOffset=0x0008,
        size=32,
        access="read-write",
        fields=[
            Field(name="DATA", description="32-bit data to be transferred to PIF-RAM", bitOffset=0, bitWidth=32)
        ]
    ),
    Register(
        name="SI_PIF_AD_WR64B",
        description="Serial Interface PIF Address Write (64-bit)",
        addressOffset=0x0010,
        size=32,
        access="read-write",
        fields=[
            Field(name="Unknown", description="Unknown", bitOffset=0, bitWidth=32)
        ]
    ),
    Register(
        name="SI_PIF_AD_RD4B",
        description="Serial Interface PIF Address Read (4-byte)",
        addressOffset=0x0014,
        size=32,
        access="read-only",
        fields=[
            Field(name="DATA", description="32-bit data to be transferred to PIF-RAM", bitOffset=0, bitWidth=32)
        ]
    ),
    Register(
        name="SI_STATUS",
        description="Serial Interface Status Register",
        addressOffset=0x0018,
        size=32,
        access="read-write",
        fields=[
            Field(name="INTERRUPT", description="SI interrupt flag", bitOffset=12, bitWidth=1),
            Field(name="DMA_STATE", description="Internal DMA state", bitOffset=8, bitWidth=4),
            Field(name="PCH_STATE", description="Internal PIF channel state", bitOffset=4, bitWidth=4),
            Field(name="DMA_ERROR", description="Set when overlapping DMA occurs", bitOffset=3, bitWidth=1),
            Field(name="READ_PENDING", description="Unknown", bitOffset=2, bitWidth=1),
            Field(name="IO_BUSY", description="Set when a direct memory write to PIF_RAM is in progress", bitOffset=1, bitWidth=1),
            Field(name="DMA_BUSY", description="Set when a DMA is in progress", bitOffset=0, bitWidth=1)
        ]
    )
]

# Create the SI Peripheral
si_peripheral = Peripheral(name="SI", description="Serial Interface", baseAddress="0xA4800000", registers=si_registers)

# Define the MI registers (same as previous code)
mi_registers_data = [
    Register(
        name="MI_MODE",
        description="MI Mode Register",
        addressOffset=0x0000,
        size=32,
        access="read-write",
        fields=[
            Field(name="Upper", description="Upper mode enabled", bitOffset=9, bitWidth=1),
            Field(name="EBus", description="EBus mode enabled", bitOffset=8, bitWidth=1),
            Field(name="Repeat", description="Repeat mode enabled", bitOffset=7, bitWidth=1),
            Field(name="RepeatCount", description="Number of bytes (minus 1) to write in repeat mode", bitOffset=0, bitWidth=7)
        ]
    ),
    Register(
        name="MI_VERSION",
        description="MI Version Register",
        addressOffset=0x0004,
        size=32,
        access="read-only",
        fields=[
            Field(name="RSP_VERSION", description="RSP hardware version", bitOffset=24, bitWidth=8),
            Field(name="RDP_VERSION", description="RDP hardware version", bitOffset=16, bitWidth=8),
            Field(name="RAC_VERSION", description="RAC hardware version", bitOffset=8, bitWidth=8),
            Field(name="IO_VERSION", description="IO hardware version", bitOffset=0, bitWidth=8)
        ]
    ),
    Register(
        name="MI_INTERRUPT",
        description="MI Interrupt Register",
        addressOffset=0x0008,
        size=32,
        access="read-write",
        fields=[
            Field(name="SP", description="SP Interrupt Mask", bitOffset=0, bitWidth=1),
            Field(name="SI", description="SI Interrupt Mask", bitOffset=1, bitWidth=1),
            Field(name="AI", description="AI Interrupt Mask", bitOffset=2, bitWidth=1),
            Field(name="VI", description="VI Interrupt Mask", bitOffset=3, bitWidth=1),
            Field(name="PI", description="PI Interrupt Mask", bitOffset=4, bitWidth=1),
            Field(name="DP", description="DP Interrupt Mask", bitOffset=5, bitWidth=1)
        ]
    ),
    Register(
        name="MI_MASK",
        description="MI Mask Register",
        addressOffset=0x000C,
        size=32,
        access="read-write",
        fields=[
            Field(name="SP", description="SP Interrupt Mask", bitOffset=0, bitWidth=1),
            Field(name="SI", description="SI Interrupt Mask", bitOffset=1, bitWidth=1),
            Field(name="AI", description="AI Interrupt Mask", bitOffset=2, bitWidth=1),
            Field(name="VI", description="VI Interrupt Mask", bitOffset=3, bitWidth=1),
            Field(name="PI", description="PI Interrupt Mask", bitOffset=4, bitWidth=1),
            Field(name="DP", description="DP Interrupt Mask", bitOffset=5, bitWidth=1)
        ]
    )
]

# Create the MI Peripheral
mi_peripheral = Peripheral(name="MI", description="MIPS Interface Controller", baseAddress="0xA4300000", registers=mi_registers_data)

# SP registers definition
sp_registers_data = [
    Register(
        name="SP_DMA_SPADDR",
        description="Address in IMEM/DMEM for a DMA transfer",
        addressOffset=0x0000,
        size=32,
        access="read-write",
        fields=[
            Field(
                name="MEM_BANK",
                description="Bank accessed by the transfer",
                bitOffset=12,
                bitWidth=1
            ),
            Field(
                name="MEM_ADDR",
                description="DMEM or IMEM address used in SP DMAs",
                bitOffset=0,
                bitWidth=12
            )
        ]
    ),
    Register(
        name="SP_DMA_RAMADDR",
        description="Address in RDRAM for a DMA transfer",
        addressOffset=0x0004,
        size=32,
        access="read-write",
        fields=[
            Field(
                name="DRAM_ADDR",
                description="RDRAM address used in the DMA transfer",
                bitOffset=0,
                bitWidth=24
            )
        ]
    ),
    Register(
        name="SP_DMA_RDLEN",
        description="Length of a DMA transfer. Writing this register triggers a DMA transfer from RDRAM to IMEM/DMEM",
        addressOffset=0x0008,
        size=32,
        access="read-write",
        fields=[
            Field(
                name="SKIP",
                description="Number of bytes to skip in RDRAM after each row",
                bitOffset=20,
                bitWidth=12
            ),
            Field(
                name="COUNT",
                description="Number of rows to transfer minus 1",
                bitOffset=12,
                bitWidth=8
            ),
            Field(
                name="RDLEN",
                description="Number of bytes to transfer for each row minus 1",
                bitOffset=0,
                bitWidth=12
            )
        ]
    ),
    Register(
        name="SP_DMA_WRLEN",
        description="Length of a DMA transfer. Writing this register triggers a DMA transfer from IMEM/DMEM to RDRAM",
        addressOffset=0x000C,
        size=32,
        access="read-write",
        fields=[
            Field(
                name="SKIP",
                description="Number of bytes to skip in RDRAM after each row",
                bitOffset=20,
                bitWidth=12
            ),
            Field(
                name="COUNT",
                description="Number of rows to transfer minus 1",
                bitOffset=12,
                bitWidth=8
            ),
            Field(
                name="WRLEN",
                description="Number of bytes to transfer for each row minus 1",
                bitOffset=0,
                bitWidth=12
            )
        ]
    ),
    Register(
        name="SP_STATUS",
        description="RSP status register",
        addressOffset=0x0010,
        size=32,
        access="read-write",
        fields=[
            Field(
                name="SIG<n>",
                description="Status of the 8 custom bits that can be freely used to communicate state between VR4300 and RSP",
                bitOffset=7,
                bitWidth=8
            ),
            Field(
                name="INTBREAK",
                description="Trigger an MI interrupt when BREAK is run",
                bitOffset=6,
                bitWidth=1
            ),
            Field(
                name="SSTEP",
                description="Single-step mode activated",
                bitOffset=5,
                bitWidth=1
            ),
            Field(
                name="IO_BUSY",
                description="RSP accessing either DMEM or IMEM",
                bitOffset=4,
                bitWidth=1
            ),
            Field(
                name="DMA_FULL",
                description="DMA transfer pending flag",
                bitOffset=3,
                bitWidth=1
            ),
            Field(
                name="DMA_BUSY",
                description="DMA transfer in progress flag",
                bitOffset=2,
                bitWidth=1
            ),
            Field(
                name="BROKE",
                description="BREAK opcode executed",
                bitOffset=1,
                bitWidth=1
            ),
            Field(
                name="HALTED",
                description="RSP running status",
                bitOffset=0,
                bitWidth=1
            )
        ]
    ),
    Register(
        name="SP_DMA_FULL",
        description="Report whether there is a pending DMA transfer (mirror of DMA_FULL bit of SP_STATUS)",
        addressOffset=0x0014,
        size=32,
        access="read-write",
        fields=[
            Field(
                name="DMA_FULL",
                description="Mirror of DMA_FULL bit in SP_STATUS",
                bitOffset=0,
                bitWidth=1
            )
        ]
    ),
    Register(
        name="SP_DMA_BUSY",
        description="Report whether there is a DMA transfer in progress (mirror of DMA_BUSY bit of SP_STATUS)",
        addressOffset=0x0018,
        size=32,
        access="read-write",
        fields=[
            Field(
                name="DMA_BUSY",
                description="Mirror of DMA_BUSY bit in SP_STATUS",
                bitOffset=0,
                bitWidth=1
            )
        ]
    ),
    Register(
        name="SP_SEMAPHORE",
        description="Register to assist implementing a simple mutex between VR4300 and RSP",
        addressOffset=0x001C,
        size=32,
        access="read-write",
        fields=[
            Field(
                name="SEMAPHORE",
                description="Semaphore bit for hardware-assisted mutex",
                bitOffset=0,
                bitWidth=1
            )
        ]
    )
]

# SP peripheral
sp_peripheral = Peripheral(
    name="SP",
    description="Signal Processor (RSP)",
    baseAddress="0xA4040000",  # base address ORed with 0xA0000000
    registers=sp_registers_data
)

pi_registers =[
    Register(
        name="PI_DRAM_ADDR",
        description="Base address of RDRAM for PI DMAs",
        addressOffset=0x00,  # Last byte of 0x04600000
        size=32,  # 32 bits register
        access="read-write",
        fields=[
            Field(
                name="DRAM_ADDR",
                description="Base address of RDRAM for PI DMAs",
                bitOffset=1,
                bitWidth=23
            )
        ]
    ),
    Register(
        name="PI_CART_ADDR",
        description="Base address of the PI bus for PI DMAs",
        addressOffset=0x04,  # Last byte of 0x04600004
        size=32,  # 32 bits register
        access="read-write",
        fields=[
            Field(
                name="CART_ADDR",
                description="Base address of the PI bus for PI DMAs",
                bitOffset=1,
                bitWidth=31
            )
        ]
    ),
    Register(
        name="PI_RD_LEN",
        description="Number of bytes, minus one, to be transferred from RDRAM to the PI bus",
        addressOffset=0x08,  # Last byte of 0x04600008
        size=32,  # 32 bits register
        access="read-write",
        fields=[
            Field(
                name="RD_LEN",
                description="Number of bytes, minus one, to be transferred from RDRAM to the PI bus",
                bitOffset=0,
                bitWidth=24
            )
        ]
    ),
    Register(
        name="PI_WR_LEN",
        description="Number of bytes, minus one, to be transferred from the PI bus, into RDRAM",
        addressOffset=0x0C,  # Last byte of 0x0460000C
        size=32,  # 32 bits register
        access="read-write",
        fields=[
            Field(
                name="WR_LEN",
                description="Number of bytes, minus one, to be transferred from the PI bus, into RDRAM",
                bitOffset=0,
                bitWidth=24
            )
        ]
    ),
    Register(
        name="PI_STATUS",
        description="Status of the PI",
        addressOffset=0x10,  # Last byte of 0x04600010
        size=32,  # 32 bits register
        access="read-write",
        fields=[
            Field(
                name="Interrupt",
                description="DMA completed",
                bitOffset=3,
                bitWidth=1
            ),
            Field(
                name="DMA_error",
                description="DMA error",
                bitOffset=2,
                bitWidth=1
            ),
            Field(
                name="IO_busy",
                description="I/O busy",
                bitOffset=1,
                bitWidth=1
            ),
            Field(
                name="DMA_busy",
                description="DMA is busy",
                bitOffset=0,
                bitWidth=1
            )
        ]
    ),
    Register(
        name="PI_BSD_DOM1_LAT",
        description="Latency value for DOM1",
        addressOffset=0x14,  # Last byte of 0x04600014
        size=32,  # 32 bits register
        access="read-write",
        fields=[
            Field(
                name="LAT",
                description="Number of RCP cycles, minus one, before the first read or write may start",
                bitOffset=0,
                bitWidth=8
            )
        ]
    ),
    Register(
        name="PI_BSD_DOM1_PWD",
        description="Pulse width value for DOM1",
        addressOffset=0x18,  # Last byte of 0x04600018
        size=32,  # 32 bits register
        access="read-write",
        fields=[
            Field(
                name="PWD",
                description="Number of RCP cycles, minus one, the /RD or /WR signals are held low",
                bitOffset=0,
                bitWidth=8
            )
        ]
    ),
    Register(
        name="PI_BSD_DOM1_PGS",
        description="Page size value for DOM1",
        addressOffset=0x1C,  # Last byte of 0x0460001C
        size=32,  # 32 bits register
        access="read-write",
        fields=[
            Field(
                name="PGS",
                description="Number of bytes that can be sequentially read/written on the bus before sending the next base address",
                bitOffset=0,
                bitWidth=4
            )
        ]
    ),
    Register(
        name="PI_BSD_DOM1_RLS",
        description="Release value for DOM1",
        addressOffset=0x20,  # Last byte of 0x04600020
        size=32,  # 32 bits register
        access="read-write",
        fields=[
            Field(
                name="RLS",
                description="Number of RCP cycles, minus one, that the /RD or /WR signals are held high between each 16-bits of data",
                bitOffset=0,
                bitWidth=2
            )
        ]
    ),
    Register(
        name="PI_BSD_DOM2_LAT",
        description="Latency value for DOM2",
        addressOffset=0x24,  # Last byte of 0x04600024
        size=32,  # 32 bits register
        access="read-write",
        fields=[
            Field(
                name="LAT",
                description="Number of RCP cycles, minus one, before the first read or write may start",
                bitOffset=0,
                bitWidth=8
            )
        ]
    ),
    Register(
        name="PI_BSD_DOM2_PWD",
        description="Pulse width value for DOM2",
        addressOffset=0x28,  # Last byte of 0x04600028
        size=32,  # 32 bits register
        access="read-write",
        fields=[
            Field(
                name="PWD",
                description="Number of RCP cycles, minus one, the /RD or /WR signals are held low",
                bitOffset=0,
                bitWidth=8
            )
        ]
    ),
    Register(
        name="PI_BSD_DOM2_PGS",
        description="Page size value for DOM2",
        addressOffset=0x2C,  # Last byte of 0x0460002C
        size=32,  # 32 bits register
        access="read-write",
        fields=[
            Field(
                name="PGS",
                description="Number of bytes that can be sequentially read/written on the bus before sending the next base address",
                bitOffset=0,
                bitWidth=4
            )
        ]
    ),
    Register(
        name="PI_BSD_DOM2_RLS",
        description="Release value for DOM2",
        addressOffset=0x30,  # Last byte of 0x04600030
        size=32,  # 32 bits register
        access="read-write",
        fields=[
            Field(
                name="RLS",
                description="Number of RCP cycles, minus one, that the /RD or /WR signals are held high between each 16-bits of data",
                bitOffset=0,
                bitWidth=2
            )
        ]
    )
]

# Define the peripheral using the list of registers
pi_peripheral = Peripheral(
    name="PI",
    description="Peripheral Interface",
    baseAddress="0xA4600000",
    registers=pi_registers
)
# Function to create an XML element
def create_element(parent, tag, text=None):
    element = ET.SubElement(parent, tag)
    if text:
        element.text = str(text)
    return element

# Function to generate XML for the registers
def generate_registers_xml(registers: List[Register], registers_elem):
    for register in registers:
        register_elem = ET.SubElement(registers_elem, "register")
        create_element(register_elem, "name", register.name)
        create_element(register_elem, "description", register.description)
        create_element(register_elem, "addressOffset", hex(register.addressOffset))
        create_element(register_elem, "size", str(register.size))
        create_element(register_elem, "access", register.access)
        
        # Create fields for this register
        fields_elem = create_element(register_elem, "fields")
        for field in register.fields:
            field_elem = ET.SubElement(fields_elem, "field")
            create_element(field_elem, "name", field.name)
            create_element(field_elem, "description", field.description)
            create_element(field_elem, "bitOffset", str(field.bitOffset))
            create_element(field_elem, "bitWidth", str(field.bitWidth))

# Function to generate the SVD file
def generate_svd_file(filename: str, peripherals: list[Peripheral]):
    # Define the SVD preamble dictionary
    svd_preamble = {
        "name": "Nintendo_64",
        "version": "1.0",
        "description": "Nintendo 64 system SVD file for the VR4300 CPU",
        "addressUnitBits": "32",
        "width": "32",
        "cpu": {
            "name": "OTHER",
            "revision": "r1p0",
            "endian": "big",
            "mpuPresent": "false",
            "fpuPresent": "true",
            "nvicPrioBits": "8",
            "vendorSystickConfig": "false"
        }
    }

    # Create the root element
    device = ET.Element("device", {"schemaVersion": "1.1", "xmlns:xs": "http://www.w3.org/2001/XMLSchema-instance"})
    
    # Create constant SVD preamble using the dictionary
    for tag, text in svd_preamble.items():
        if isinstance(text, dict):
            # Create the 'cpu' element with its sub-elements
            cpu_elem = create_element(device, "cpu")
            for sub_tag, sub_text in text.items():
                create_element(cpu_elem, sub_tag, sub_text)
        else:
            create_element(device, tag, text)
    
    peripherals_elem = create_element(device, "peripherals")
    
    # Loop through the peripherals list and generate the XML dynamically for each
    for peripheral in peripherals:
        peripheral_elem = create_element(peripherals_elem, "peripheral")
        create_element(peripheral_elem, "name", peripheral.name)
        create_element(peripheral_elem, "description", peripheral.description)
        create_element(peripheral_elem, "baseAddress", peripheral.baseAddress)
        
        addressBlock_elem = create_element(peripheral_elem, "addressBlock")
        create_element(addressBlock_elem, "offset", "0x0000")
        create_element(addressBlock_elem, "size", hex(peripheral.calculate_size_of_registers()))
        create_element(addressBlock_elem, "usage", "registers")
        
        registers_elem = create_element(peripheral_elem, "registers")
        
        # Loop through the registers and generate the XML dynamically for each peripheral
        generate_registers_xml(peripheral.registers, registers_elem)
    
    # Generate and save prettified XML
    tree = ET.ElementTree(device)
    raw_xml = minidom.parseString(ET.tostring(device)).toprettyxml(indent="    ")
    
    with open(filename, "w") as f:
        f.write(raw_xml)
    
    print(f"Generated SVD file: {filename}")

# Output filename path
output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "svd")
os.makedirs(output_dir, exist_ok=True)
output_filename = os.path.join(output_dir, "n64.svd")

# List of peripherals to include (MI and SI)
peripherals = [mi_peripheral, si_peripheral, sp_peripheral, pi_peripheral]

# Generate the SVD file with both MI and SI peripherals
generate_svd_file(output_filename, peripherals)
print(f"SVD file generated at: {output_filename}")
