    # state function: continuously read input for latest manipulation configuration
    def read_input(self):
        try:
            user_input = input(
                "(Proxy) Enter parameters (c_drop_chance, c_delay_chance, c_delay_time, s_drop_chance, s_delay_chance, s_delay_time): "
            )
            if self.terminate_flag.is_set():
                self.state = "success"
                return
            
            input_parts = user_input.split(",")
            parameters = {}
            for part in input_parts:
                key, value = part.split(":")
                key = key.strip()
                value = value.strip()
                parameters[key] = value

            def cap_value(value, min_val, max_val):
                return max(min_val, min(max_val, int(value)))

            def cap_delay_time(value, min_val, max_val):
                return max(min_val, min(max_val, float(value)))

            self.shared_config["client_drop"] = cap_value(parameters.get("c_drop_chance", self.shared_config["client_drop"]), 0, 100)
            self.shared_config["client_delay"] = cap_value(parameters.get("c_delay_chance", self.shared_config["client_delay"]), 0, 100)
            self.shared_config["client_delay_time"] = cap_delay_time(parameters.get("c_delay_time", self.shared_config["client_delay_time"]), 0, 100000)

            self.shared_config["server_drop"] = cap_value(parameters.get("s_drop_chance", self.shared_config["server_drop"]), 0, 100)
            self.shared_config["server_delay"] = cap_value(parameters.get("s_delay_chance", self.shared_config["server_delay"]), 0, 100)
            self.shared_config["server_delay_time"] = cap_delay_time(parameters.get("s_delay_time", self.shared_config["server_delay_time"]), 0, 100000)

            print(f"(Proxy-Keyboard) Parameters updated:")
            print(f"  Client: drop={self.shared_config['client_drop']}%, delay={self.shared_config['client_delay']}%, delay_time={self.shared_config['client_delay_time']} ms")
            print(f"  Server: drop={self.shared_config['server_drop']}%, delay={self.shared_config['server_delay']}%, delay_time={self.shared_config['server_delay_time']} ms")

        except ValueError as ve:
            print(f"(Proxy) Invalid input format: {ve}")
        except KeyboardInterrupt:
            print("(Proxy) Shutting down server...")
            self.terminate_flag.set()
            self.state = "success"
        except Exception as e:
            print(f"(Proxy) Error: {e}")
