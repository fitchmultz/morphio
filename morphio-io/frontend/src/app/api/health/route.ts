import { NextResponse } from "next/server";
import logger from "@/lib/logger";

export async function GET() {
	logger.info("Health check called");
	return NextResponse.json({ status: "ok" });
}

export async function HEAD() {
	return NextResponse.json({ status: "ok" });
}
