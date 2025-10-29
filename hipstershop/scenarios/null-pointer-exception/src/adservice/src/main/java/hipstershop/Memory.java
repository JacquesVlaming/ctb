package hipstershop;
        import java.io.IOException;
        import java.lang.management.ManagementFactory;
        import java.lang.management.MemoryMXBean;

public class Memory {

    public static void main(String[] args) throws IOException, InterruptedException {
        System.out.println(ManagementFactory.getPlatformMXBean(MemoryMXBean.class).getHeapMemoryUsage().getMax());
    }

}
