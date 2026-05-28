export {};
import { Button, Tooltip } from "antd";
import { MoonOutlined, SunOutlined } from "@ant-design/icons";
import { useTheme } from "../theme/ThemeProvider";

export function ThemeToggle() {
  const { mode, toggle } = useTheme();
  return (
    <Tooltip title={mode === "light" ? "切换深色模式" : "切换浅色模式"}>
      <Button
        type="text"
        shape="circle"
        icon={mode === "light" ? <MoonOutlined /> : <SunOutlined />}
        onClick={toggle}
      />
    </Tooltip>
  );
}
