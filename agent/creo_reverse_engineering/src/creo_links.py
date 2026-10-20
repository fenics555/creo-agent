    def _extract_bom_links(self):
        """
        BOM links: assembly -> component.
        Looking for 'FeatDefsCmp' or similar component data in assemblies.
        """
        # We look for sections that define component data in assemblies
        # Typically 'FeatDefsCmp' or 'Comp_Data'
        for section_name, (offset, length) in self.toc.items():
            if "FeatDefsCmp" in section_name or "Comp_Data" in section_name:
                section_data = self.raw_data[offset : offset + length]
                self._parse_component_section(section_name, section_data, offset)

    def _parse_component_section(self, section_name: str, data: bytes, base_offset: int):
        """Parses component data to find target component names and instance names."""
        # Implementation based on pattern: [comp_data] -> comp_name\0 [instance_name]\0
        # We use the decoder to navigate the structured block
        curr = 0
        while curr < len(data):
            # We search for the pattern of a component record
            # In assemblies, components are often identified by their name and instance
            val, next_off, v_type, name = self.decoder.decode_next_value(data, curr)
            if not name or v_type == "EOF":
                break
            
            # If we find a component name, the next value in the record is often the instance name
            if v_type == "STRING" and len(name) > 2:
                # Check if the next value is an instance name (string)
                next_val, next_next_off, next_v_type, next_name = self.decoder.decode_next_value(data, next_off)
                
                if next_v_type == "STRING" and next_name:
                    # We found a component + instance
                    # source is the assembly (or current feature)
                    # target is the component
                    # For simplicity, we use a generic 'ASSEMBLY' or the current section context
                    source = "ASSEMBLY_CONTEXT" 
                    self.edges.append(CreoEdge(
                        source=source,
                        target=next_name,
                        edge_type="contains_via_instance",
                        metadata={"instance_name": next_name, "comp_name": name}
                    ))
                elif next_v_type == "STRING":
                    # Just a component
                    self.edges.append(CreoEdge(
                        source="ASSEMBLY_CONTEXT",
                        target=name,
                        edge_type="contains",
                        metadata={"comp_name": name}
                    ))
                
                curr = next_next_off if next_next_off > curr else next_off + 1
            else:
                curr = next_off if next_off > curr else curr + 1

