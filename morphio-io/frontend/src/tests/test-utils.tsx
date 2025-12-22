import { type RenderOptions, render } from "@testing-library/react";
import { ThemeProvider } from "next-themes";
import type React from "react";
import type { ReactElement } from "react";
import { AuthProvider } from "@/contexts/AuthContext";

// Create a custom render function that includes all necessary providers
const AllTheProviders = ({ children }: { children: React.ReactNode }) => {
	return (
		<ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
			<AuthProvider>{children}</AuthProvider>
		</ThemeProvider>
	);
};

const customRender = (
	ui: ReactElement,
	options?: Omit<RenderOptions, "wrapper">,
) => render(ui, { wrapper: AllTheProviders, ...options });

// Re-export everything from testing-library
export * from "@testing-library/react";

// Override the render method
export { customRender as render };
