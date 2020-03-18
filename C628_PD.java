import java.util.*;
public class C628_PD {

    public static void main(String[] args) {
        // TODO Auto-generated method stub
        Scanner in = new Scanner(System.in);
        long u = in.nextLong();
        long v = in.nextLong();
        if(u>v||u%2!=v%2)
        {
            System.out.println(-1);
            return;
        }
        if(u==v)
        {
            if(u==0)
                System.out.println(0);
            else
            {
                System.out.println(1);
                System.out.println(u);
            }
            return;
        }
        long x = (v-u)/2;
        if((u&x)!=0)
        {
            System.out.println(3);
            System.out.println(u+ " "+x+" "+x );
        }
        else
        {
            System.out.println(2);
            System.out.println((u^x)+ " "+x );
        }
        //System.out.println(1);
    }

}

