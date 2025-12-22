import { EventEmitter } from "events";
import logger from "./logger";

type EventHandler = (...args: unknown[]) => void;

class LoggingEventEmitter extends EventEmitter {
	// Map to track original listener → wrapped listener for proper cleanup
	private listenerMap = new Map<EventHandler, EventHandler>();

	constructor() {
		super();
		// Increase max listeners to prevent warnings
		this.setMaxListeners(50);
	}

	emit(event: string | symbol, ...args: unknown[]): boolean {
		// Log event name only (not args) to avoid leaking sensitive data
		logger.debug(`Event emitted: ${String(event)}`);
		return super.emit(event, ...args);
	}

	on(event: string | symbol, listener: EventHandler): this {
		logger.debug(`Event listener added: ${String(event)}`);

		// Create wrapped listener with performance logging
		const wrappedListener: EventHandler = (...args) => {
			const start = performance.now();
			listener(...args);
			logger.performance(
				`Event listener execution: ${String(event)}`,
				performance.now() - start,
			);
		};

		// Store mapping for cleanup
		this.listenerMap.set(listener, wrappedListener);

		return super.on(event, wrappedListener);
	}

	off(event: string | symbol, listener: EventHandler): this {
		logger.debug(`Event listener removed: ${String(event)}`);

		// Look up the wrapped listener and remove it
		const wrappedListener = this.listenerMap.get(listener);
		if (wrappedListener) {
			this.listenerMap.delete(listener);
			return super.off(event, wrappedListener);
		}

		// Fallback: try to remove the original listener directly
		return super.off(event, listener);
	}

	once(event: string | symbol, listener: EventHandler): this {
		logger.debug(`One-time event listener added: ${String(event)}`);

		// For once(), the listener auto-removes after execution
		const wrappedListener: EventHandler = (...args) => {
			const start = performance.now();
			listener(...args);
			logger.performance(
				`One-time event listener execution: ${String(event)}`,
				performance.now() - start,
			);
			// Clean up the map entry after one-time execution
			this.listenerMap.delete(listener);
		};

		this.listenerMap.set(listener, wrappedListener);
		return super.once(event, wrappedListener);
	}

	// Override removeListener (alias for off) for consistency
	removeListener(event: string | symbol, listener: EventHandler): this {
		return this.off(event, listener);
	}
}

const eventEmitter = new LoggingEventEmitter();

export default eventEmitter;
